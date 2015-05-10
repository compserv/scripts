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
import ldap.filter
import copy
from optparse import OptionParser
from subprocess import Popen, PIPE

import mmlist

# FIXME: Make this parameter with default
POSITIONS_FILE = "/home/hkn/compserv/positions"
POSITIONS = []

GIDS = {}

def script_exit(error_code):
    mmlist.script_exit(error_code)

def error_exit(str):
    script_exit(1)
    raise Exception(str)

def warn(s):
    print "[WARNING] %s" % s

def check_root():
    return os.geteuid() == 0

# Returns true if login is already the name of a mailing list.
def check_maillists(login):
    cmd = "/home/hkn/compserv/scripts/mmlist.py -l"
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.stdout
    maillists = [line[:-1] for line in output.readlines()]

    return login in maillists

def init_ldap():
    try:
        l = ldap.open("127.0.0.1")
        #l = ldap.initialize('ldapi:///')

        # you should  set this to ldap.VERSION2 if you're using a v2 directory
        l.protocol_version = ldap.VERSION3
        # Pass in a valid username and password to get
        # privileged directory access.
        # If you leave them as empty strings or pass an invalid value
        # you will still bind to the server but with limited privileges.

        username = "cn=admin,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
        basedn = "ou=people,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
        with open('/etc/libnss-ldap.secret', 'r') as passfile:
             password = passfile.readline()

        # Any errors will throw an ldap.LDAPError exception
        # or related exception so you can ignore the result
        l.simple_bind(username, password)
    except ldap.LDAPError, e:
        print e
        # handle error however you like

    return l


# Returns true if login already exists. False otherwise.
def check_login(login):
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

    if len(result_set) > 1:
        print "Warning, multiple old users found."

    return len(result_set) >= 1

# Returns true if group is valid with LDAP.
def check_group(group):
    l = init_ldap()
    ## The next lines will also need to be changed to support your search requirements and directory
    baseDN = "ou=groups,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = None
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

    if len(result_set) > 1:
        print "Warning, multiple old groups found."

    return len(result_set) >= 1

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

def unset_ldap_group(username, group):
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

    old = result_set[0][0][1]['memberUid']
    new = copy.deepcopy(old)
    if username in new:
        new.remove(username)

    oldattr = {'memberUid' : old}
    newattr = {'memberUid' : new}

    # The dn of our existing entry/object
    dn = "cn=%s,ou=groups,dc=hkn,dc=eecs,dc=berkeley,dc=edu" % group

    # Convert place-holders for modify-operation using modlist-module
    ldif = modlist.modifyModlist(oldattr,newattr)

    # Do the actual modification
    l.modify_s(dn,ldif)

    l.unbind_s()

def set_ldap_group(username, group):
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
  if name in groups:
      return groups[name]
  else:
      return name


class NewUser(object):
    OBJECT_CLASS = ['top','posixAccount','shadowAccount', 'account']
    DEFAULT_USER_PASS = 'aDifferentSecret'
    DEFAULT_USER_HASH = '8ab0c4dc762c91682d3aed0d9ed38b2179f1b1e2'
    HKN_GID = '200'
    DEFAULT_SHELL = '/bin/bash'

    DN_TEMPLATE = "uid=%s,ou=people,dc=hkn,dc=eecs,dc=berkeley,dc=edu"

    def __init__(self, login, first_name, last_name, uidNumber=None):
        self.login = login
        self.first_name = first_name
        self.last_name = last_name
        self.uidNumber = uidNumber

    def get_attrs(self, l):
        attrs = {'objectClass': NewUser.OBJECT_CLASS,
                'cn': self.get_real_name(),
                'userPassword': NewUser.DEFAULT_USER_PASS,
                'uid': self.login,
                'gidNumber': NewUser.HKN_GID,
                'homeDirectory': self.get_homedir(),
                'loginShell': NewUser.DEFAULT_SHELL
                }
        print "Adding uid:", self.uidNumber

        if self.uidNumber:
            attrs['uidNumber'] = self.uidNumber
        else:
            attrs['uidNumber'] = str(find_next_uid(l))
        return attrs

    def get_real_name(self):
        return self.first_name + ' ' + self.last_name

    def get_dn(self):
        return NewUser.DN_TEMPLATE % self.login

    def get_homedir(self):
        return '/home/%s' % self.login

class NewUserException(Exception): pass

def warn_and_raise_nue(s):
    warn(s)
    raise NewUserException(s)

def create_gafyd_user(new_user):
    from gdata.apps.service import AppsService

    G_EMAIL = "hkn-ops@hkn.eecs.berkeley.edu"
    G_PASSWORD = "a89Kl.o3"
    G_DOMAIN = "hkn.eecs.berkeley.edu"

    s = AppsService(email=G_EMAIL, password=G_PASSWORD, domain=G_DOMAIN)
    s.ProgrammaticLogin()

    try:
        s.RetrieveUser(new_user.login)
    except:
        s.CreateUser(new_user.login, new_user.last_name, new_user.first_name,
                new_user.DEFAULT_USER_HASH, password_hash_function='SHA-1')


def create_user(l, new_user):
    if check_login(new_user):
        warn_and_raise_nue('Given login (%s) already exists.' % new_user)

    if check_maillists(new_user):
        warn_and_raise_nue('Given login (%s) is already a mailing list.' % new_user)


    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = modlist.addModlist(new_user.get_attrs(l))

    # Do the actual synchronous add-operation to the ldapserver
    l.add_s(new_user.get_dn(), ldif)

    # Its nice to the server to disconnect and free resources when done
    l.unbind_s()

def create_homedir(new_user):
    SKEL_DIR = '/etc/skel'
    PROCMAILRC = '.procmailrc'
    PROCMAILRC_TEMPLATE = \
"""MAILDIR=$HOME/mail

:0:
* ^X-Spam-Status: Yes
/dev/null

:0:
! %s@hkn.eecs.berkeley.edu.test-google-a.com
"""

    if not check_root():
        warn_and_raise_nue("You're not root... This will be very hard to do, so I'm giving up.")

    homedir = new_user.get_homedir()
    if os.path.isdir(homedir):
        warn_and_raise_nue('User (%s) already has home directory.' % new_user.login)

    #os.mkdir(homedir)
    os.system('cp -R %s %s' % (SKEL_DIR, homedir))
    os.mkdir(os.path.join(homedir, 'mail'))

    f = open(os.path.join(homedir, PROCMAILRC), 'w')
    f.write(PROCMAILRC_TEMPLATE % new_user.login)
    f.close()

    os.system('chown -R %s:hkn %s' % (new_user.login, homedir))

def set_comm_membership(login, comm):
    if not check_group(to_ldap_group(comm)):
        warn_and_raise_nue('Given group/committee (%s) does not exist.' % comm)

    set_ldap_group(login, to_ldap_group(comm))
    if comm == 'compserv':
        set_ldap_group(login, to_ldap_group('ops'))

def unset_comm_membership(login, comm):
    if not check_group(to_ldap_group(comm)):
        warn_and_raise_nue('Given group/committee (%s) does not exist.' % comm)

    unset_ldap_group(login, to_ldap_group(comm))
    if comm == 'compserv':
        unset_ldap_group(login, to_ldap_group('ops'))

def set_mail_membership(login, comm, is_cmember, not_current):
    old_virtual, old_aliases = mmlist.init()

    if comm == 'ops':
        aliases = set(['ops'])
    else:
        aliases = set([comm + ('-cmembers' if is_cmember else '-officers')])
    if comm == 'compserv':
        aliases.add('ops')

    if not not_current:
        if comm != 'pres' and comm != 'vp':
            aliases.add('current-non-pvp')

        if is_cmember:
            aliases.add('current-cmembers')
        else:
            aliases.add('current-officers')

        aliases.add('current-' + comm)

    for alias in aliases:
        if alias not in old_virtual:
            warn_and_raise_nue('Alias for committee (%s) could not be found.' % alias)

        mmlist.insert_email(login, alias, True)

def unset_mail_membership(login, comm, is_cmember, not_current):
    old_virtual, old_aliases = mmlist.init()

    if comm == 'ops':
        aliases = set(['ops'])
    else:
        aliases = set([comm + ('-cmembers' if is_cmember else '-officers')])
    if comm == 'compserv':
        aliases.add('ops')

    if not not_current:
        if comm != 'pres' and comm != 'vp':
            aliases.add('current-non-pvp')

        if is_cmember:
            aliases.add('current-cmembers')
        else:
            aliases.add('current-officers')

        if comm == 'compserv' or comm == 'studrel' or comm == 'bridge' or comm == 'pres' or comm == 'vp':
            aliases.add('current-' + comm)

    for alias in aliases:
        if alias not in old_virtual:
            warn_and_raise_nue('Alias for committee (%s) could not be found.' % alias)

        if login not in old_virtual[comm]:
            try:
                mmlist.delete_email(login, alias)
            except Exception as e:
                warn("Could not delete email: " + str(e))

def unmod_user(login, comm, is_cmember, not_current):
    unset_comm_membership(login, comm)
    unset_mail_membership(login, comm, is_cmember, not_current)

def add_new_user(login, comm, email, first_name, last_name, is_cmember, not_current):
    l = init_ldap()

    new_user = NewUser(login, first_name, last_name)
    create_user(l, new_user)
    create_homedir(new_user)
    set_comm_membership(new_user.login, comm)
    set_mail_membership(new_user.login, comm, is_cmember, not_current)
    create_gafyd_user(new_user)

#Used to add back users who were lost when hkn was restarted in 05/12
def add_dead_user(login, comm, first_name, last_name, uid):
    l = init_ldap()

    new_user = NewUser(login, first_name, last_name, uid)
    create_user(l, new_user)
    set_comm_membership(new_user.login, comm)

def mod_user(login, comm, is_cmember, not_current):
    set_comm_membership(login, comm)
    set_mail_membership(login, comm, is_cmember, not_current)

def wipe_current_mlists(mlist):
    #mlists = ['current-bridge', 'current-cmembers', 'current-compserv',
    #'current-non-pvp', 'current-officers', 'current-pres', 'current-studrel',
    #'current-vp']

    #for mlist in mlists:
    #    try:
    #        mmlist.wipe_current_mlist(mlist)
    #    except:
    #        pass
    mmlist.wipe_all_current_mlists(mlist)

def change_username(login, new_name):
    l = init_ldap()
    baseDN = "ou=people,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = None
    login = ldap.filter.escape_filter_chars(login)
    new_name = ldap.filter.escape_filter_chars(new_name)
    searchFilter = "uid={0}".format(login)

    try:
        userSearch = l.search_s(baseDN, searchScope, searchFilter, retrieveAttributes)

        if len(userSearch) > 1:
            print "Warning, multiple users found."
        else:
            dn = userSearch[0][0]
            new_rdn = "uid={0}".format(new_name)
            l.rename_s(dn, new_rdn)

    except ldap.LDAPError, e:
        print e

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

def parse_options():
    parser = OptionParser()
    parser.add_option('-a', action='store_true', dest='new_user', default=False,
            help="this signals that a new user should be created")
    parser.add_option('-m', action='store_true', dest='mod_user', default=False,
            help="this signals that an existing user is being modified")
    parser.add_option('-s', action='store_true', dest='figure_out_user',
            default=False,
            help="this signals that the script should figure out whether the user exists or not")
    parser.add_option('-u', action='store_true', dest='unmod_user',
            default=False,
            help="this signals that an existing user is being unmodified")
    #parser.add_option('-d', action='store_true', dest='del_user', default=False,
    #        help="this signals that a user should be deleted")
    parser.add_option('-l', dest='login', metavar='login',
            help="the user login")
    parser.add_option('-c', dest='comm', metavar='committee',
            help="the committee name")
    parser.add_option('-e', dest='email', metavar='email',
            help="the user email")
    parser.add_option('--nf', dest='first_name', metavar='first name',
            help="the user's first name")
    parser.add_option('--nl', dest='last_name', metavar='last name',
            help="the user's last name")
    parser.add_option('-r', dest='new_name', metavar='new name',
            help="the user's new username")
    parser.add_option('-y', action='store_true', dest='is_cmember',
            default=False,
            help="add this flag if this is for a committee member")
    parser.add_option('-z', action='store_true', dest='not_current',
            default=False,
            help="don't add the member to the 'current' mailing lists.")
    parser.add_option('-w', dest='wipe_mlists', metavar='maillist',
            default=False,
            help="wipe 'current' mailing lists after storing contents"
                 "to previous-* and to maillist-*.")
    options, args = parser.parse_args()
    return (options, args)

def main():
    def check_val(val, s):
        if not val:
            error_exit(s)

    if not check_root():
        error_exit("You're not root... This will be very hard to do, so I'm giving up.")

    opts, args = parse_options()
    if opts.new_user:
        check_val(opts.login, 'this option needs login (-l)')
        check_val(opts.comm, 'this option needs committee (-c)')
        check_val(opts.email, 'this option needs email (-e)')
        check_val(opts.first_name, 'this option needs first name (-nf)')
        check_val(opts.last_name, 'this option needs last name (-nl)')

        add_new_user(opts.login, opts.comm, opts.email, opts.first_name,
                opts.last_name, opts.is_cmember, opts.not_current)

    elif opts.mod_user:
        check_val(opts.login, 'this option needs login (-l)')
        check_val(opts.comm, 'this option needs committee (-c)')

        mod_user(opts.login, opts.comm, opts.is_cmember, opts.not_current)

    elif opts.unmod_user:
        check_val(opts.login, 'this option needs login (-l)')
        check_val(opts.comm, 'this option needs committee (-c)')

        unmod_user(opts.login, opts.comm, opts.is_cmember, opts.not_current)

    elif opts.figure_out_user:
        check_val(opts.login, 'this option needs login (-l)')
        check_val(opts.comm, 'this options needs committee (-c)')

        if check_login(opts.login):
            mod_user(opts.login, opts.comm, opts.is_cmember, opts.not_current)
        else:
            check_val(opts.email, 'this option needs email (-e)')
            check_val(opts.first_name, 'this option needs first name (-nf)')
            check_val(opts.last_name, 'this option needs last name (-nl)')

            add_new_user(opts.login, opts.comm, opts.email, opts.first_name,
                    opts.last_name, opts.is_cmember, opts.not_current)

    elif opts.wipe_mlists is not False:
        check_val(opts.wipe_mlists, 'this option needs a maillist to '
                                    'save to (-w)')
        wipe_current_mlists(opts.wipe_mlists)

    elif opts.new_name is not None:
        check_val(opts.login, 'this option needs login (-l)')
        check_val(opts.new_name, 'this option needs a target name (-r)')

        change_username(opts.login, opts.new_name)

    script_exit(0)

if __name__ == "__main__":
    main()
    #parse_positions()
    #set_group_membership('amber', to_ldap_group('ops'))
    #print check_login("arjun")
    #print check_login("richardxia")
    #print check_login("awong")
    #print POSITIONS
    #parse_positions()
    #officers, new_officers = parse("new_officers")
    #create_user(new_officers, "awong")
    #set_group_membership('awong', 'compserv')
    #print find_next_uid(init_ldap())
    #print find_next_uid(init_ldap())
    #hashes()

