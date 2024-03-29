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

def init_ldap():
    try:
        l = ldap.initialize('ldapi:///')

        # you should  set this to ldap.VERSION2 if you're using a v2 directory
        l.protocol_version = ldap.VERSION3
        # Pass in a valid username and password to get
        # privileged directory access.
        # If you leave them as empty strings or pass an invalid value
        # you will still bind to the server but with limited privileges.

        username = "cn=admin,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
        with open('/etc/libnss-ldap.secret', 'r') as passfile:
             password = passfile.readline().strip()

        # Any errors will throw an ldap.LDAPError exception
        # or related exception so you can ignore the result
        l.simple_bind_s(username, password)
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
    baseDN = "ou=groups,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = ["memberUid"]
    username = ldap.filter.escape_filter_chars(username)
    group = ldap.filter.escape_filter_chars(group)
    groupsFilter = "cn={0}".format(group)

    try:
        groupSearch = l.search_s(baseDN, searchScope, groupsFilter, retrieveAttributes)

        if len(groupSearch) != 1:
            print "Group not found!"
            return

        (groupdn, data) = groupSearch[0]
        if 'memberUid' in data:
            group_members = data['memberUid']
            if username in group_members:
                new_members = copy.deepcopy(group_members)
                new_members.remove(username)

                oldattr = {'memberUid' : group_members}
                newattr = {'memberUid' : new_members}

                ldif = modlist.modifyModlist(oldattr,newattr)
                l.modify_s(groupdn, ldif)

    except ldap.LDAPError, e:
        print e
    finally:
        l.unbind_s()

def set_ldap_group(username, group):
    l = init_ldap()
    baseDN = "ou=groups,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = ["memberUid"]
    username = ldap.filter.escape_filter_chars(username)
    group = ldap.filter.escape_filter_chars(group)
    groupsFilter = "cn={0}".format(group)

    try:
        groupSearch = l.search_s(baseDN, searchScope, groupsFilter, retrieveAttributes)

        if len(groupSearch) != 1:
            print "Group not found!"
            return

        (groupdn, data) = groupSearch[0]
        if 'memberUid' in data:
            group_members = data['memberUid']
            new_members = copy.deepcopy(group_members)
            new_members.append(username)

            oldattr = {'memberUid' : group_members}
            newattr = {'memberUid' : new_members}

            ldif = modlist.modifyModlist(oldattr,newattr)
            l.modify_s(groupdn, ldif)

    except ldap.LDAPError, e:
        print e
    finally:
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

#new content here June 2015 to try to update to new API
SERVICE_ACCOUNT_EMAIL = "162858711208-gtvmconl0et75fgpapdsnuscdt1pjf9o@developer.gserviceaccount.com"
SERVICE_ACCOUNT_PKCS12_FILE_PATH = "/root/other-homes/gafyd/pygafyd/pygafyd-3d9ca0095976.p12"
import httplib2
import pprint
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
G_EMAIL = "hkn-ops@hkn.eecs.berkeley.edu"
G_PASSWORD = "a89Kl.o3"
G_DOMAIN = "hkn.eecs.berkeley.edu"
def createDirectoryService():
    f = file(SERVICE_ACCOUNT_PKCS12_FILE_PATH, 'rb')
    key = f.read()
    f.close()
    credentials = SignedJwtAssertionCredentials(SERVICE_ACCOUNT_EMAIL, key, scope='https://www.googleapis.com/auth/admin.directory.user', sub=G_EMAIL)
    http = httplib2.Http()
    http = credentials.authorize(http)
    return build('admin', 'directory_v1', http=http)


def create_gafyd_user(new_user):
    # from gdata.apps.service import AppsService

    # s = AppsService(email=G_EMAIL, password=G_PASSWORD, domain=G_DOMAIN)
    # s.ProgrammaticLogin()
    s = createDirectoryService()

    useremail = new_user.login + "@hkn.eecs.berkeley.edu"

    try:
        u = s.users()
        request = u.get(userKey=useremail)
        i = request.execute()
        # s.RetrieveUser(new_user.login)
    except:
        # s.CreateUser(new_user.login, new_user.last_name, new_user.first_name, new_user.DEFAULT_USER_HASH, password_hash_function='SHA-1')
        try:
            body = {}
            body["primaryEmail"] = useremail
            namedict = {"fullName" : new_user.first_name + " " + new_user.last_name, "givenName" : new_user.first_name, "familyName" : new_user.last_name}
            body["name"] = namedict
            body["password"] = new_user.DEFAULT_USER_HASH
            body["hashFunction"] = "SHA-1"
            request = u.insert(body=body)
            i = request.execute()
        except Exception, e:
            print "Exception while creating " + new_user.login + " : "
            print str(e)

def create_user(l, new_user):
    if check_login(new_user):
        warn_and_raise_nue('Given login (%s) already exists.' % new_user)

    # Convert our dict to nice syntax for the add-function using modlist-module
    ldif = modlist.addModlist(new_user.get_attrs(l))

    # Do the actual synchronous add-operation to the ldapserver
    l.add_s(new_user.get_dn(), ldif)

    # Its nice to the server to disconnect and free resources when done
    l.unbind_s()

def create_homedir(new_user):
    SKEL_DIR = '/etc/skel'

    if not check_root():
        warn_and_raise_nue("You're not root... This will be very hard to do, so I'm giving up.")

    homedir = new_user.get_homedir()
    if os.path.isdir(homedir):
        warn_and_raise_nue('User (%s) already has home directory.' % new_user.login)

    #os.mkdir(homedir)
    os.system('cp -R %s %s' % (SKEL_DIR, homedir))
    os.mkdir(os.path.join(homedir, 'mail'))

    create_procmailrc(homedir, new_user.login)

    os.system('chown -R %s:hkn %s' % (new_user.login, homedir))

def create_procmailrc(homedir, login):
    PROCMAILRC = '.procmailrc'
    PROCMAILRC_TEMPLATE = \
"""MAILDIR=$HOME/mail

:0:
* ^X-Spam-Status: Yes
/dev/null

:0:
! {0}@hkn.eecs.berkeley.edu.test-google-a.com
"""
    with open(os.path.join(homedir, PROCMAILRC), 'w') as f:
        f.write(PROCMAILRC_TEMPLATE.format(login))

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

def unmod_user(login, comm, is_cmember, not_current):
    unset_comm_membership(login, comm)

def add_new_user(login, comm, email, first_name, last_name, is_cmember, not_current):
    l = init_ldap()

    new_user = NewUser(login, first_name, last_name)
    create_user(l, new_user)
    create_homedir(new_user)
    set_comm_membership(new_user.login, comm)
    create_gafyd_user(new_user)

#Used to add back users who were lost when hkn was restarted in 05/12
def add_dead_user(login, comm, first_name, last_name, uid):
    l = init_ldap()

    new_user = NewUser(login, first_name, last_name, uid)
    create_user(l, new_user)
    set_comm_membership(new_user.login, comm)

def mod_user(login, comm, is_cmember, not_current):
    set_comm_membership(login, comm)

def change_username(login, new_name):
    l = init_ldap()
    peopleDN = "ou=people,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    groupsDN = "ou=groups,dc=hkn,dc=eecs,dc=berkeley,dc=edu"
    searchScope = ldap.SCOPE_SUBTREE
    ## retrieve all attributes - again adjust to your needs - see documentation for more options
    retrieveAttributes = None
    groupsRetrieveAttributes = ['memberUid']
    login = ldap.filter.escape_filter_chars(login)
    new_name = ldap.filter.escape_filter_chars(new_name)
    uidFilter = "uid={0}".format(login)
    groupsFilter = "cn=*"

    oldDirectory = "/home/{0}".format(login)
    newDirectory = "/home/{0}".format(new_name)

    try:
        # Search for the user to see if it exists
        userSearch = l.search_s(peopleDN, searchScope, uidFilter, retrieveAttributes)

        if len(userSearch) > 1:
            print "Warning, multiple users found."
            return
        elif len(userSearch) == 0:
            print "User not found."
            return

        # Rename the user
        dn = userSearch[0][0]
        new_rdn = "uid={0}".format(new_name)
        l.rename_s(dn, new_rdn)

        new_dn = "{0},{1}".format(new_rdn, peopleDN)

        # Rename the user's home directory
        os.rename(oldDirectory, newDirectory)

        # Rename the home directory in LDAP
        ldif = [(ldap.MOD_REPLACE, "homeDirectory", [newDirectory])]
        l.modify_s(new_dn, ldif)

        create_procmailrc(newDirectory, new_name)

        # Change the username in every group it's in
        groupSearch = l.search_s(groupsDN, searchScope, groupsFilter, groupsRetrieveAttributes)

        for (groupdn, data) in groupSearch:
            if 'memberUid' in data:
                group_members = data['memberUid']
                if login in group_members:
                    new_members = copy.deepcopy(group_members)
                    new_members[new_members.index(login)] = new_name

                    oldattr = {'memberUid' : group_members}
                    newattr = {'memberUid' : new_members}

                    ldif = modlist.modifyModlist(oldattr,newattr)
                    l.modify_s(groupdn, ldif)

    except ldap.LDAPError, e:
        print e
    finally:
        l.unbind_s()

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

    elif opts.wipe_mlists:
        check_val(opts.wipe_mlists, 'this option needs a maillist to '
                                    'save to (-w)')

    elif opts.new_name is not None:
        check_val(opts.login, 'this option needs login (-l)')
        check_val(opts.new_name, 'this option needs a target name (-r)')

        change_username(opts.login, opts.new_name)

    script_exit(0)

if __name__ == "__main__":
    main()

