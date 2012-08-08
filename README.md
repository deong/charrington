charrington
===========

Like the eponymous character in &quot;1984&quot;, charrington watches who you talk to and tells 
Big Brother (DataBase). That is, it pulls down specified contact groups from one or more Google 
Contacts accounts and writes them into BBDB format.

Charrington currently requires a working Python 2.7.x installation.


Features
-----------
* Supports multiple Google accounts simultaneously
* Allows only specific contact groups to be fetched
* Doesn't barf on non-ASCII characters
* Syncs most information (phone numbers, postal addresses, organization, etc.) 


Usage
-----------
Charrington requires the Google Data Client modules for Python, current available from
(http://code.google.com/apis/gdata/docs/client-libraries.html). I have developed and tested
against gdata-2.0.17 specifically.

Charrington comes with a sample configuration file. Copy that file to $HOME/.charringtonrc and edit
it using your favorite text editor. Note that it requires your login and password to be stored in 
plain text, so be sure to set permissions appropriately ("chmod 0600 ~/.charringtonrc"), or simply
delete your information after you've synced and put it back in as needed to keep things synced.

Once you have your account information set up run

    charrington.py -g

This tells charrington to query all configured accounts for contact group information. It should
print the name of each group you have along with an "Atom ID". Copy the Atom ID (it will be a URI)
into your ~/.charringtonrc file for each group you want to fetch the contacts from.

Once you have the groups configured in your rc file, you can simply run

    charrington.py > bbdb-file

Be sure to save a backup of your existing file and manually verify that the one produced by 
Charrington works correctly in BBDB and contains all the expected contacts.

Charrington also saves the Google-ID field associated with each contact into BBDB's notes alist.
This will be necessary to do any sort of two-way syncing, but right now, it's mostly useful for
debugging why something went wrong with one of your contacts. If an address or name is formatted
badly in BBDB, you can take the contact id field and pass it to charrington like

    charrington -c http://www.google.com/m8/feeds/contacts/deong%40cataclysmicmutation.com/base/4e7e4e20b3c9744  

and you can see the raw XML that Google is sending back for each contact. You can then try to
match up the fields to see what might be wrong, either to report or fix a bug or just to work
around the issue by changing the contact in the web interface. Note that because Charrington
has to log you in to the correct account to fetch a contact, and you may have more than one
account, it tries to guess which account to use by pulling the login name out of the contact ID
and matching it with one of your configured accounts. I'm not sure if the heuristic is guaranteed
to work all the time, but it seems to work for all of my accounts at least.


Limitations
-----------
* Charrington is not a true synchronization tool. You can't currently edit your contacts in BBDB
and have them pushed back up to Google's servers -- all editing must be done using the web
interface to Google Contacts.

* Duplicates aren't currently handled in any special way -- you just get multiple records in your
BBDB file. This typically doesn't cause too many problems, and you can always run bbdb-show-duplicates,
and manually clean things up, but your cleanups will be overwritten the next time you run charrington.
This one is on the list of things to fix soon.

* Charrington mostly fills out the information that makes sense in BBDB, but there is some information
that isn't currently being used. Most notably, things like job titles are currently ignored.
