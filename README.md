charrington
===========

Like the eponymous character in &quot;1984&quot;, charrington watches who you talk to and tells 
Big Brother (DataBase). That is, it pulls down specified contact groups from one or more Google 
Contacts accounts and writes them into BBDB format.



Features
===========
* Supports multiple Google accounts simultaneously
* Allows only specific contact groups to be fetched
* Doesn't barf on non-ASCII characters



Usage
===========
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



Limitations
===========
* Charrington is not a true synchronization tool. You can't currently edit your contacts in BBDB
and have them pushed back up to Google's servers -- all editing must be done using the web
interface to Google Contacts.

* Duplicates aren't currently handled in any special way -- you just get multiple records in your
BBDB file. This typically doesn't cause too many problems, and you can always run bbdb-show-duplicates,
and manually clean things up, but your cleanups will be overwritten the next time you run charrington.
This one is on the list of things to fix soon.

* Charrington mostly fills out the information that makes sense in BBDB, but there is some information
that isn't currently being used. Most notably, things like job titles are currently ignored.

* Postal address formatting is a little wonky at the moment. Some contacts seem to lose street numbers,
international addresses aren't formatted in the expected way, etc. Some of these are clearly just bugs
I need to track down. Others may be longer-term issues.
