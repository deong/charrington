**Important: As of May, 2015, Charrington isn't working, due to Google removing
  support for ClientLogin. At some point, I'll port it to using OAuth, but my
  real job likely won't allow for the time in the next month or so. Sorry for
  the inconvenience.**

charrington
===========

Like the eponymous character in &quot;1984&quot;, charrington watches who you talk to and tells 
Big Brother (DataBase). That is, it pulls down specified contact groups from one or more Google 
Contacts accounts and writes them into BBDB format. Recent versions can also write out a mutt
aliases file.

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

As of 2014-01-19, Charrington supports contact groups as well. If you have contacts assigned to 
groups in Google, the group name will be canonicalized (lowercased and with all special characters
removed or converted to underscores) and written into the resulting BBDB file as a mail-alias.
You can then insert the following lines into your `.gnus` or similar file and type the mail alias
to expand to all members of the group. (Thanks to Pierre Crescenzo for suggesting this feature).

    (add-hook 'mail-setup-hook 'bbdb-define-all-aliases)
    (add-hook 'message-setup-hook 'bbdb-define-all-aliases)
    
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

For a simple aliases file for use with Mutt, you can run 

    charrington.py -m > ~/.mutt/aliases

Note however that there are some drawbacks imposed by the way that Mutt works. Most notably, 
aliases must be unique, whereas Google allows multiple email addresses for a given contact. With
BBDB, this is no problem -- I simply create one record with a list of addresses, and tab completion
in Emacs clients will display a list to choose from. This isn't possible with Mutt. If multiple
email addresses are given for a single record, it is treated as a group, and Mutt will send mail 
to every address.

The way that Charrington supports multiple addresses for a contact is pretty simple and a bit
hamfisted. The alias is just the lowercased first name. In case of duplicates, it simply creates a new alias for every email address that appears in the Google Contacts accounts being synced. Because
the nickname fields must be unique, it just starts appending numbers to the first name field in all
successive matches. For example, if you have the following contacts,

    John Doe <jdoe@example.com, jdoe@workcompany.com>
    John Smith <jsmith@pocahontas.net, john.smith@example.com>
    John Henry Johnson <jhj@steeldrivers.net>

Charrington might produce aliases like

    john John Doe <jdoe@example.com>
    john1 John Doe <jdoe@workcompany.com>
    john2 John Smith <jsmith@pocahontas.net>
    john3 John Smith <john.smith@example.com>
    johnhenry John Henry Johnson <jhj@steeldrivers.net>

Note the treatment of middle names. If you specifiy a middle name, it typically (always?) is treated
as part of the first name by Charrington.

This method is not foolproof. If a first name has special characters, the results are somewhat
arbitrary. I simply call the `lower()` method on the name and remove literal spaces. 


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
