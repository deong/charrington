#!/usr/bin/env python
# -*- coding: latin-1 -*-
#
# charrington.py
#
# Charrington syncs your Google contacts into a local BBDB file.
#
# In 1984, Charrington was the member of the thought police who told Big Brother
# about Winston and Julia's secret apartment. In this context, he tells Big Brother
# (DataBase) about your contacts. OK, so it's a stretch...I was bored.
#
# -------------------------------------------------------------------------------------
# Usage:
# 
# There are a few wrinkles to this process, particularly since Google has tied
# Google+ in so tightly with your contacts. You almost certainly don't want every
# random person you've circled in your address book, but that's the default behavior.
# It is possible to limit the groups you pull down, and the system group "My Contacts"
# probably contains what you want. However, selecting which group to pull is not
# especially friendly. You have to give the group ID, which is a long URI with a
# relatively meaningless number at the end.
#
# The expected way for you to use Charrington is to set up a configuration file
# under ~/.charringtonrc with your login credentials for each account you want to
# fetch. Then run
#
#	  charrington -g
#
# which tells Charrington to pull down all your group information rather than try
# to fetch your contacts. You should see, for each group, a name and and ID string.
# Find the groups you want, and then paste the entire ID string into your .charringtonrc
# file (under the correct account, of course).
#
# Once that is done, you can simply run
#
#	  charrington > ~/.bbdb
#
# to sync your Google contacts back down into your local BBDB file.
#
# -------------------------------------------------------------------------------------
#
# Known Issues:
#
# It doesn't yet do anything special with duplicates. You can always run bbdb-show-duplicates
# and fix things after the fact, but they'll reappear as soon as you run charrington
# again.
#
# There's no two-way syncing yet. I usually add new contacts infrequently enough that
# it's not a huge problem to do it via the web interface, but it would be nice to have
# some sort of rudimentary syncing at least.
#
# There's some information in Google that could probably fit into BBDB that I'm not
# currently doing anything with (job titles, that sort of thing).
#
# Note also that charrington currently requires Python 2.7.x.
# ------------------------------------------------------------------------------------
# 
# # Copyright 2012 Deon Garrett <deong@cataclysmicmutation.com>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#	  http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import argparse
import string
import re
import ConfigParser
import atom.data
import gdata.data
import gdata.contacts.client
import gdata.contacts.data


class Contact:
	def __init__(self):
		self.first_name = ""
		self.last_name = ""
		# Google does have a "nickname" field, but I'm currently not using it
		self.nickname = []
		self.organization = ""
		# list of tuples, each of the form (label, number)
		self.phone_numbers = []
		# list of tuples, each of the form (label, street, city, state, zip, country)
		self.addresses = []
		# list of tuples, each of the form (label, address, is_primary)
		self.email = []
		# last modification time
		self.timestamp = None
		# google contact id
		self.id = None
		# list of groups the contact appears in
		self.groups = []


class ContactGroup:
	def __init__(self):
		self.href = ""
		self.name = ""
		self.is_system = False


# fields for phone number records
PHONE_LABEL=0
PHONE_NUMBER=1

# fields for address records
ADDR_LABEL=0
ADDR_STREET=1
ADDR_NEIGHBORHOOD=2
ADDR_CITY=3
ADDR_STATE=4
ADDR_ZIP=5
ADDR_COUNTRY=6

# fields for email records
EMAIL_LABEL=0
EMAIL_ADDRESS=1
EMAIL_PRIMARY=2


# reads the user's config file and returns a configuration object
def load_config():
	cp = ConfigParser.ConfigParser()
	cp.read(os.path.expanduser("~/.charringtonrc"))
	return cp


# return a list of accounts, each represented as a map containing the account name,
# login, and password
def get_accounts(cp):
	accounts = []
	for section in cp.sections():
		# for each account, parse the list of groups to fetch
		if cp.has_option(section, "groups"):
			accounts.append({"name": section,
							 "login": cp.get(section, "login"),
							 "password": cp.get(section, "password"),
							 "groups": map(lambda x : x.strip(), cp.get(section, "groups").split(","))})
		else:
			accounts.append({"name": section,
							 "login": cp.get(section, "login"),
							 "password": cp.get(section, "password")})
			
	return accounts


# return a map of all contact groups on the server
def get_all_contact_groups(acct):
	gdc = gdata.contacts.client.ContactsClient(source='charrington')
	gdc.ClientLogin(acct["login"], acct["password"], gdc.source)

	cgroups = {}
	elements = gdc.GetGroups()
	for i, element in enumerate(elements.entry):
		cg = ContactGroup()
		cg.href = element.id.text
		cg.name = element.title.text
		if element.system_group != None:
			cg.is_system = True
		else:
			cg.is_system = False
		cgroups[cg.href] = cg
	return cgroups


# fetch all the user's contacts from a given account, printing them as BBDB records
def get_all_contacts(acct, groups):
	gdc = gdata.contacts.client.ContactsClient(source='charrington')
	gdc.ClientLogin(acct["login"], acct["password"], gdc.source)

	contacts = []
	for group in acct["groups"]:
		# set up a query for the contacts in the current group and fetch them
		query = gdata.contacts.client.ContactsQuery()
		query.max_results = 5000
		query.group = group
		feed = gdc.GetContacts(q=query)

		for i, entry in enumerate(feed.entry):
			# I chose to skip any items where there was no name entered.
			if not entry.name:
				continue

			# create a contact object by parsing the element data
			con = make_contact(entry)

			# now match the group id against the list of known groups from the server.
			# if there's a match, add the group's name to the list of groups for the contact.
			# skip the system groups entirely.
			if entry.group_membership_info != None:
				for cgroup in entry.group_membership_info:
					if cgroup.href in groups.keys() and not groups[cgroup.href].is_system:
						con.groups.append(groups[cgroup.href])

			# and finally add the new contact to the list
			contacts.append(con)
	return contacts


# given a raw record from the gdata apis for a given contact, populate a
# friendlier data structure that can be more easily manipulated.
def make_contact(entry):
	con = Contact()
	# names are handled a bit weirdly here. BBDB doesn't really support
	# any rich representation of names -- it's pretty much First/Last. So
	# if a contact has "Additional Names" in Google's schema, I arbitrarily
	# chose to append them to the first name field
	if entry.name:
		con.first_name = safe_text(entry.name.given_name)
		con.last_name = safe_text(entry.name.family_name)
		if entry.name.additional_name:
			con.first_name += " " + entry.name.additional_name.text
	if entry.nickname:
		con.nickname = [entry.nickname]
	if entry.organization and entry.organization.name:
		con.organization = entry.organization.name.text
	for ph_entry in entry.phone_number:
		con.phone_numbers.append(parse_phone(ph_entry))
	for addr_entry in entry.structured_postal_address:
		con.addresses.append(parse_address(addr_entry))
	for email in entry.email:
		con.email.append(parse_email(email))

	con.timestamp = canonicalize_date(safe_text(entry.updated))
	con.id = entry.id.text
	return con


# take an instance of a gdata.data.PhoneNumber and return the label and number
#
# Note that the gdata class is very cumbersome, as it is completely unstructured;
# you only have XML fragments. The number is simply the text of the XML node, which
# is easy enough to get, but the label appears to only be present as a part of a
# schema URL embedded in the "rel" attribute.
def parse_phone(phone_entry):
	phone_number = phone_entry.text
	label = get_label_from_schema(phone_entry)
	return (label, phone_number)
	

# take an instance of a gdata.data.StructuredPostalAddress and return the label and
# address information. Note that some of my addresses show the city under the
# "neighborhood" field instead of the city, for reasons I'm not sure of. The hack
# I put in to deal with this is the following:
#
# If the city is empty but the neighborhood isn't, treat the neighborhood as the city.
# If both are present, write the neighborhood as line two of the street address.
def parse_address(addr_entry):
	label = get_label_from_schema(addr_entry)
	if addr_entry.po_box:
		street = safe_text(addr_entry.po_box)
	else:
		street = safe_text(addr_entry.street)

	# figure out neighborhood/city distinction.
	neighborhood = None
	if addr_entry.neighborhood:
		if not addr_entry.city:
			city = addr_entry.neighborhood.text
		else:
			neighborhood = addr_entry.neighborhood.text
			city = addr_entry.city.text
	else:
		city = safe_text(addr_entry.city)
		
	region = safe_text(addr_entry.region)
	postcode = safe_text(addr_entry.postcode)
	country = safe_text(addr_entry.country)
	return (label, street, neighborhood, city, region, postcode, country)


# take an instance of a gdata.data.Email and return the label, address, and primary
# flag for the address
def parse_email(email_entry):
	label = get_label_from_schema(email_entry)
	return (label, email_entry.address, email_entry.primary)


# return the final component of a schema URL
#
# The contacts API often uses the schema to denote labels (e.g., someone's "Home"
# phone number is stored in an XML node with an attribute that looks like
# rel="http://schemas.google.com/g/2005#home" -- note the trailing "#...."
# characters.
#
# This function grabs that last bit of the string, title-cases it, and returns
# it as a label.
def get_label_from_schema(entry):
	if entry.rel:
		if "label=" in entry.rel:
			return entry.rel.rsplit("label=", 1)[1].title()
		else:
			return entry.rel.rsplit("#", 1)[1].title()


# normalize a structured component
#
# In the Google APIs, most things are classes. So if you call address.city, you
# get back a structure rather than a string. Calling address.city.text works, but
# needs to be protected by a null check. This function simply takes one of these
# structures, checks to see if it's None, and returns either "" or its text
# attribute accordingly
def safe_text(entry):
	if not entry:
		return ""
	else:
		return ", ".join(entry.text.split("\n"))


# take a timestamp returned by Google (like "2011-12-04T01:16:11.081Z") and pull
# out just the YYYY-MM-DD components. If the input string doesn't start with that
# matching format, just return the string unmodified
def canonicalize_date(ts):
	pat = re.compile("(\d{4}-\d{2}-\d{2})")
	m = pat.match(ts)
	if m:
		return m.group(0)
	else:
		return ts
	

# take a group name and return a lowercased version without special characters
def canonicalize_group_name(gname):
	return gname.translate(string.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ ", 
											"abcdefghijklmnopqrstuvwxyz_"), 
						   string.punctuation)


# print a contact out in human readable form
def print_contact(contact):
	if contact.nickname:
		print(contact.first_name+" "+contact.last_name+" ("+contact.nickname+")")
	else:
		print(contact.first_name+" "+contact.last_name)
	if contact.organization:
		print(contact.organization)
	for phone in contact.phone_numbers:
		print(phone[PHONE_LABEL]+": "+phone[PHONE_NUMBER])
	for addr in contact.addresses:
		print(addr[ADDR_LABEL])
		print("\t"+addr[ADDR_STREET])
		if addr[ADDR_NEIGHBORHOOD]:
			print("\t"+addr[ADDR_NEIGHBORHOOD])
		print("\t"+addr[ADDR_CITY]+", "+addr[ADDR_STATE]+" "+addr[ADDR_ZIP])
		print("\t"+addr[ADDR_COUNTRY])
	for email in contact.email:
		print("{}: {:30} {}".format(email[EMAIL_LABEL], email[EMAIL_ADDRESS], "*" if email[EMAIL_PRIMARY] else ""))
	print("")


# return a contact in BBDB format
#
# The basic structure is as follows: (note this must all be on a single line)
#	  ["first" "last" ["nicknames"] "company" (["phone_label" "phone_number"] ...) \
#		  (["addr_label" ["street"] "city" "region" "postcode"] ...) ("email_address" ...) \
#		  (notes_alist) nil]
#		  
# See http://bbdb.sourceforge.net/bbdb.html#SEC67 for more information on the format.
def format_contact_bbdb(contact):
	# write first name, last name, and company -- ignore any nicknames
	str = u"[\"{fn}\" \"{ln}\" nil \"{co}\"".format(fn=contact.first_name,
													ln=contact.last_name,
													co=contact.organization)

	# write the list of phone numbers
	if len(contact.phone_numbers) == 0:
		str += u" nil"
	else:
		str += u" ("
		first_pass = True
		for phone in contact.phone_numbers:
			if not first_pass:
				str += u" "
			str += u"[\"{lb}\" \"{num}\"]".format(lb=phone[PHONE_LABEL],
												  num=phone[PHONE_NUMBER])
			first_pass = False
		str += u")"

	# write the list of postal addresses
	if len(contact.addresses) == 0:
		str += u" nil"
	else:
		str += u" ("
		first_pass = True
		for addr in contact.addresses:
			if not first_pass:
				str += u" "
			if addr[ADDR_NEIGHBORHOOD]:
				str += u"[\"{lb}\" (\"{st}\" \"{nb}\") \"{ci}\" \"{rg}\" \"{pc}\" \"{co}\"]"\
					   .format(lb=addr[ADDR_LABEL], st=addr[ADDR_STREET], nb=addr[ADDR_NEIGHBORHOOD],
							   ci=addr[ADDR_CITY], rg=addr[ADDR_STATE], pc=addr[ADDR_ZIP], co=addr[ADDR_COUNTRY])
			else:
				str += u"[\"{lb}\" (\"{st}\") \"{ci}\" \"{rg}\" \"{pc}\" \"{co}\"]"\
					   .format(lb=addr[ADDR_LABEL], st=addr[ADDR_STREET], ci=addr[ADDR_CITY], rg=addr[ADDR_STATE],
							   pc=addr[ADDR_ZIP], co=addr[ADDR_COUNTRY])
			first_pass = False
		str += u")"

	# write out the email addresses
	if len(contact.email) == 0:
		str += u" nil"
	else:
		str += u" ("
		first_pass = True
		for email in contact.email:
			if not first_pass:
				str += u" "
			str += u"\"{em}\"".format(em=email[EMAIL_ADDRESS])
			first_pass = False
		str += u")"

	# Notes field contains an alist of assorted data; for now, I'm just storing
	# the modification date (YYYY-MM-DD)
	str += u" ("
	str += u"(timestamp . \"{ts}\")".format(ts=contact.timestamp)
	str += u" (google-id . \"{id}\")".format(id=contact.id)
	if len(contact.groups) > 0:
		str += u" (mail-alias . \"{alias}\")".format(alias=', '.join([canonicalize_group_name(x.name) for x in contact.groups]))
	str += u")"

	# there appears to be an additional "nil" at the end...no idea what it's for
	str += u" nil"
	
	# close the opening bracket
	str += u"]"
	return str


# write out a complete bbdb file for the given contact group
def print_bbdb_header():
	print(";; -*-coding: utf-8-emacs;-*-")
	print(";;; file-version: 6")
		

# print the list in bbdb format
def output_bbdb_file(contacts):
	print_bbdb_header()
	printed = set()
	for contact in contacts:
		# don't print the same contact twice
		if contact.id in printed:
			continue
		# don't print entries that have no email addresses
		if not contact.email:
			continue
		print(format_contact_bbdb(contact).encode("utf-8"))
		printed.add(contact.id)



# print the list in mutt format
def output_mutt_aliases(contacts):
	nicks = {}
	printed = set()
	for contact in contacts:
		# don't print the same contact twice
		if contact.id in printed:
			continue
		# don't print entries that have no email addresses
		if not contact.email:
			continue
		# now iterate over each address, and create a unique alias
		for email in contact.email:
			fname = contact.first_name.lower().split(" ")[0]
			nick = fname
			if fname in nicks:
				nick += str(nicks[fname])
				nicks[fname] += 1
			else:
				nicks[fname] = 1
			print(format_contact_mutt(nick, contact.first_name, contact.last_name, email[EMAIL_ADDRESS]).encode("utf-8"))
		printed.add(contact.id)


# format a contact entry in mutt's alias format
def format_contact_mutt(nickname, first_name, last_name, addr):
	str = u"alias {nick} {first} {last} <{email}>".format(nick=nickname,
		first=first_name, last=last_name, email=addr)
	return str


# print out information for all your contact groups in a given account
def display_groups(acct):
	gdc = gdata.contacts.client.ContactsClient(source='charrington')
	gdc.ClientLogin(acct["login"], acct["password"], gdc.source)
	feed = gdc.GetGroups()
	for entry in feed.entry:
		print("Group Name: "+entry.title.text)
		print("Atom Id: "+entry.id.text+"\n")


# print out the information for a specific contact
# This is basically a debugging tool. If you need to figure out why a particular entry
# in the BBDB file looks borked, pass it's google id in here and you can print the
# raw XML data returned from Google for that contact.
def lookup_contact(acct, contact_id):
	gdc = gdata.contacts.client.ContactsClient(source='charrington')
	gdc.ClientLogin(acct["login"], acct["password"], gdc.source)
	return gdc.GetContact(contact_id)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Download Google Contacts into BBDB")
	parser.add_argument("-g", "--show-groups", action="store_true", help="Display information on contact groups.")
	parser.add_argument("-c", "--contact", help="View raw XML returned by Google Contacts API for a given contact ID.")
	parser.add_argument("-m", "--mutt", action="store_true", help="Write output in Mutt alias format instead of BBDB")
	args = parser.parse_args()

	cp = load_config()
	accts = get_accounts(cp)
	
	if args.show_groups:
		for acct in accts:
			print("========================================================================")
			print("Account: "+acct["name"])
			display_groups(acct)
			print("========================================================================")
		print("\nFor each group you wish to sync, copy the AtomID (the entire URI) into your\n"
			  "~/.charringtonrc file under the matching account section. Multiple groups should\n"
			  "be separated by commas.")
		exit(0)
		
	elif args.contact:
		# figure out which account to query based on the login field in the Id URI
		pat = re.compile("http://www.google.com/m8/feeds/contacts/([^/]+)/")
		match = pat.match(args.contact)
		if match:
			login = match.group(1).replace("%40", "@")
			for acct in accts:
				if acct["login"] == login:
					print(lookup_contact(acct, args.contact))
					exit(0)
			print("No matching account to query for contact: "+args.contact)
			
	else:
		# build a map of all groups (across all accounts)
		# note that if you have groups with the same name in different accounts, they will be merged
		# in the generated bbdb file
		groups = {}
		for acct in accts:
			acctgroups = get_all_contact_groups(acct)
			for groupid, group in acctgroups.items():
				groups[groupid] = group 

		# build list of all contacts across all accounts
		contacts = []
		for acct in accts:
			contacts += get_all_contacts(acct, groups)

		# sort and remove dups
		contacts.sort(key=lambda x : x.last_name.lower())
		
		if args.mutt:
			output_mutt_aliases(contacts)
		else:
			output_bbdb_file(contacts)
