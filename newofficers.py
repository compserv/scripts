#!/usr/bin/env python

# Making sure that the new aliases file generated is correct
# TODO: Create GAFYD accounts automatically for new users. This can be done by 
# using the existing GAFYD script in /home/gafyd/pygafyd by appending a
# password hash for the user in /home/gafyd/gafyd.log

import sys
import string
import os.path
import os
import re
import ldap
import ldap.modlist as modlist
import copy

# FIXME: Make this parameter with default
POSITIONS_FILE = "/home/hkn/compserv/positions"
POSITIONS = []

GIDS = {}

def init_ldap():
    try:
        l = ldap.open("127.0.0.1")
        
        # you should  set this to ldap.VERSION2 if you're using a v2 directory
        l.protocol_version = ldap.VERSION3
        # Pass in a valid username and password to get 
        # privileged directory access.
        # If you leave them as empty strings or pass an invalid value
        # you will still bind to the server but with limited privileges.
         
        username = "cn=admin,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
        password  = "Eyu3KxxevumLB9H1"
        
        # Any errors will throw an ldap.LDAPError exception 
        # or related exception so you can ignore the result
        l.simple_bind(username, password)
    except ldap.LDAPError, e:
        print e
        # handle error however you like

    return l


# Returns true if login already exists. False otherwise.
def check_old_users(login):
    l = init_ldap()
    ## The next lines will also need to be changed to support your search requirements and directory
    baseDN = "ou=people,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = None 
    searchFilter = "uid=%s" % login

    try:
        ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        result_set = []
        while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                ## here you don't have to append to a list
                ## you could do whatever you want with the individual entry
                ## The appending to list is just for illustration. 
                if result_type == ldap.RES_SEARCH_ENTRY:
                    result_set.append(result_data)
    except ldap.LDAPError, e:
        print e

    if len(result_set) == 1:
        return True
    elif len(result_set) > 1:
        print "Warning, multiple old users found."
        return True
    else:
        return False

def parse_positions():
    f = open(POSITIONS_FILE, "r")
    global POSITIONS
    POSITIONS = [position.strip() for position in f.readlines()]
    f.close()

# Returns true if group is valid with LDAP. Must be valid group, "examfiles" no
# longer exists and should not return True.
def check_group(position):
    return position in POSITIONS

# Parses through the officers file and returns a hashtable containing the
# information of the officers
def parse(fname):
    f = open(fname, "r")
    lines = f.readlines()

    officers = {}
    new_officers = {}
    for linenum in range(len(lines)):
        line = lines[linenum]
        description = line.split()

        if len(description) == 2:
            login = description[0]
            position = description[1]
            new_officer = False
        elif len(description) >= 5:
            login = description[0]
            position = description[1]
            inst_login = description[2]
            email = description[3]
            real_name = string.join(description[4:])
            new_officer = True
        else:
            print "WARN: Ignoring linenum " + str((linenum + 1))
            continue

        # Check to see if it's a comment.
        if login[0] == "#":
            continue

        # Error checking:
        # 1. New officers' logins should not collide with previous users.
        # 2. Old officers should already have accounts.
        # 3. Groups should be valid.
        # So apparently, the committees listed in the new_officers file are
        #   mailing list aliases, but not the actual LDAP group name
        if new_officer:
            if check_old_users(login):
                print "ERROR: Already existing user with login " + login
                #sys.exit(1)
        else:
            if not check_old_users(login):
                print "ERROR: Old officer's login is not found " + login
                sys.exit(1)
        if not check_group(position):
            print "ERROR: Position " + position + "  not found for " + login
            print "If this is a new officer position, you must manually add it to the aliases file before running this script"
            sys.exit(1)

        if new_officer:
            officers[login] = (new_officer, login, position, inst_login, email, real_name)
            new_officers[login] = (new_officer, login, position, inst_login, email, real_name)
        else:
            officers[login] = (new_officer, login, position)


    f.close()

    return officers, new_officers

# Backs up all files that will be edited
def backup():
    os.system("ldapsearch -x -b \"dc=hkn, dc=eecs, dc=berkeley, dc=edu\" -h 127.0.0.1 -D \"cn=admin,dc=hkn,dc=eecs,dc=berkeley,dc=edu\" -y ldp \"(objectclass=*)\" > ldap_backup")

def find_next_uid(l):
    ## The next lines will also need to be changed to support your search requirements and directory
    baseDN = "ou=people,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = ["uidNumber"]
    searchFilter = "uidNumber=*"

    try:
        ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        result_set = []
        while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                ## here you don't have to append to a list
                ## you could do whatever you want with the individual entry
                ## The appending to list is just for illustration. 
                if result_type == ldap.RES_SEARCH_ENTRY:
                    result_set.append(result_data)
    except ldap.LDAPError, e:
        print e

    uids = [int(x[0][1]['uidNumber'][0]) for x in result_set]
    uids.sort()
    return uids[-1] + 1

def hashes():
    l = init_ldap()
    ## The next lines will also need to be changed to support your search requirements and directory
    baseDN = "ou=people,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = ["uid", "userPassword"]
    searchFilter = "uidNumber=*"

    try:
        ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        result_set = []
        while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                ## here you don't have to append to a list
                ## you could do whatever you want with the individual entry
                ## The appending to list is just for illustration. 
                if result_type == ldap.RES_SEARCH_ENTRY:
                    result_set.append(result_data)
    except ldap.LDAPError, e:
        print e

    stuff = [(x[0][1]['userPassword'][0], x[0][1]['uid'][0] ) for x in result_set]
    g = open('hashes', 'w')
    for thing in stuff:
        g.write(thing[0] + " " + thing[1] + "\n")

def set_group_membership(username, group):
    l = init_ldap()
    ## The next lines will also need to be changed to support your search requirements and directory
    baseDN = "ou=groups,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = ["memberUid"]

    searchFilter = "cn=%s" % group
    try:
        ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        result_set = []
        while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                ## here you don't have to append to a list
                ## you could do whatever you want with the individual entry
                ## The appending to list is just for illustration. 
                if result_type == ldap.RES_SEARCH_ENTRY:
                    result_set.append(result_data)
    except ldap.LDAPError, e:
        print e

    print group, username
    old = result_set[0][0][1]['memberUid']
    new = copy.deepcopy(old)
    if username not in new:
        new.append(username)

    oldattr = {'memberUid' : old}
    newattr = {'memberUid' : new}

    # The dn of our existing entry/object
    dn = "cn=%s,ou=groups,dc=hkn,dc=eecs,dc=berkeley,dc=edu" % group
    
    # Convert place-holders for modify-operation using modlist-module
    ldif = modlist.modifyModlist(oldattr,newattr)
    
    # Do the actual modification 
    l.modify_s(dn,ldif)

    l.unbind_s()


# Add officer to the list of users in LDAP and update their passwords
def create_user(new_officers, login):
    print new_officers[login]
    l = init_ldap()
    nextUid = find_next_uid(l)
    # The dn of our new entry/object

    dn="uid=%s,ou=people,dc=hkn, dc=eecs, dc=berkeley, dc=edu" % login

    # A dict to help build the "body" of the object
    attrs = {}
    attrs['objectClass'] = ['top','posixAccount','shadowAccount', 'account']
    attrs['cn'] = new_officers[login][5]
    attrs['userPassword'] = 'aDifferentSecret'
    attrs['uid'] = login
    attrs['uidNumber'] = str(nextUid)
    attrs['gidNumber'] = '200'
    attrs['homeDirectory'] = '/home/%s' % login
    attrs['loginShell'] = '/bin/bash'


    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = modlist.addModlist(attrs)

    # Do the actual synchronous add-operation to the ldapserver
    l.add_s(dn,ldif)

    # Its nice to the server to disconnect and free resources when done
    l.unbind_s()

def add_user_home(new_officers, login):
    HOME = "/home/"
    SKEL = "/etc/skel/"
    PROCMAILRC = ".procmailrc"

    homedir = os.path.join(HOME, login)

    if os.path.isdir(homedir):
        print login + " really shouldn't already have a home directory...ignoring"
        return
    
    os.mkdir(homedir)
    os.system("cp " + SKEL + ".* " + homedir)
    os.mkdir(os.path.join(homedir, "mail"))

    # Create procmailrc
    f = open(os.path.join(homedir, PROCMAILRC), "w")
    f.write("""MAILDIR=$HOME/mail

:0:
* ^X-Spam-Status: Yes
/dev/null

#:0c
""")
    f.write("#! " + new_officers[login][4] + "\n\n")
    
    f.write(":0:\n")
    f.write("! " + login + "@hkn.eecs.berkeley.edu.test-google-a.com\n")
    f.close()

def create_new_aliases(officers):
    old = open('/etc/postfix/virtual', 'r')
    new = open('./virtual', 'w')

    # Let's do this a totally different way
    # Let's generate a hash of aliases and people that should be in each of them
    # i.e. aliases['act-officers'] = ['pssandhu', 'adit']
    # i.e. aliases['indrel-auditors'] = ['cphsu']
    # One minor problem is that we need an existing label for new committees
    # You'll have to manually add it to the real aliases file before running the script

    aliases = {}
    for officer_name in officers:
        officer = officers[officer_name]
        officer_position = officer[2]
        #print officer_position
        if (officer_position+'-officers') not in aliases:
            aliases[officer_position+'-officers'] = []
        aliases[officer_position+'-officers'].append(officer)
        if officer_position == 'pub':
            if 'indrel-auditors' not in aliases:
                aliases['indrel-auditors'] = []
            if 'act-auditors' not in aliases:
                aliases['act-auditors'] = []
            if 'tutoring-auditors' not in aliases:
                aliases['tutoring-auditors'] = []
            aliases['indrel-auditors'].append(officer)
            aliases['act-auditors'].append(officer)
            aliases['tutoring-auditors'].append(officer)
        elif officer_position == 'compserv':
            if 'root' not in aliases:
                aliases['root'] = []
            if 'hkn-ops' not in aliases:
                aliases['hkn-ops'] = []
            if 'hkn-osp' not in aliases:
                aliases['hkn-osp'] = []
            aliases['root'].append(officer)
            aliases['hkn-ops'].append(officer)
            aliases['hkn-osp'].append(officer)

    # Parse the file line by line, and if the line begins with one of the aliases
    # above, then we should add the appropriate people
    #position_prefix = re.compile('^[^:]-officers:')
    for line in old.readlines():
        #label = line.split(':')
        # Changing this to work on virtual file, split first on whitespace
        label = line.split()
        if label and label[0] in aliases.keys():
            # Should figure out which position it is and write out new officers
            alias = label[0]
            new.write(alias+'    ')
            names = ' '.join(label[1:])
            existing_officers = [existing_officer.strip() for existing_officer in names.split(',')]
            for officer in aliases[alias]:
                username = officer[1]
                if username not in existing_officers:
                    new.write(username+', ')
            new.write(names+'\n')
        else:
            # Copy over old line
            new.write(line)
    new.close()
    old.close()


def chown_homes(name):
    print "sudo chown -R %s:hkn /home/%s" % (name, name)
    os.system("sudo chown -R %s:hkn /home/%s" % (name, name))

def to_ldap_group(name):
  """ Given a committee mailing list name, returns the corresponding user group.
  i.e. to_ldap_group('deprel') => 'deptrel'
  """
  groups = {
      "pres":"pres",
      "vp":"vp",
      "treas":"treas",
      "rsec":"rsec",
      "csec":"csec",
      "bridge":"bridge",
      "act":"act",
      "tutoring":"tutor",
      "pub":"pub",
      "compserv":"compserv",
      "indrel":"indrel",
      "deprel":"deptrel",
      "alumrel":"alumni",
      "studrel":"studrel",
      "serv":"serv"
      }
  try:
    return groups[name]
  except:
    print "Could not find LDAP group name for " + name

def main():
    if len(sys.argv) != 2:
        print "Usage: newofficers.py <file>"
        return

    parse_positions()
    fname = sys.argv[1]
    officers, new_officers = parse(fname)

    for key in new_officers:
        create_user(new_officers, key)
        add_user_home(new_officers, key)
        chown_homes(key)
        set_group_membership(key, to_ldap_group(officers[key][2]))

    # Add people to the correct mailing lists:
    create_new_aliases(officers)

if __name__ == "__main__":
    main()
    #print check_old_users("arjun")
    #print check_old_users("richardxia")
    #print check_old_users("awong")
    #print POSITIONS
    #parse_positions()
    #officers, new_officers = parse("new_officers")
    #create_user(new_officers, "awong")
    #set_group_membership('awong', 'compserv')
    #print find_next_uid(init_ldap())
    #print find_next_uid(init_ldap())
    #hashes()
    
