#!/usr/bin/env python


# Options needed:
# -l something to list all the mailing lists
# -b (list all lists a given member is on)
# -r makes -b recursive

import subprocess as sp
from optparse import OptionParser

MMLIST_LOCATION = '/home/hkn/compserv/scripts/'
MAILMAN_LOCATION = '/usr/lib/mailman/bin/'

def parse_options():
    parser = OptionParser()
    parser.add_option('-l', '--list',  action='store_true', dest='list', default=False,
            help='list all mailing lists')

    parser.add_option('-r', '--recursive',  action='store_true', dest='recursive', default=False,
            help='make -b act recursively')

    parser.add_option('-b', dest='expansion', metavar='expansion',
            help='list mailing lists that the specified address (either an individual\'s email or another list) is on')

    options, args = parser.parse_args()
    return (options, args)

def runproc(cmd, indata=None):
    proc = sp.Popen('python ' + cmd, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
    if indata is not None:
        proc.communicate(input=indata)
    out = proc.stdout.read()
    err = proc.stderr.read()
    return out, err

def mmlist(*args):
    return runproc(MMLIST_LOCATION + "mmlist.py " + " ".join(args))

def mmlist_list_lists():
    return mmlist("-l")

def mailman(*args, **keywords):
    if "indata" in keywords.keys():
        return runproc(MAILMAN_LOCATION + " ".join(args), indata = keywords["indata"])
    else:
        return runproc(MAILMAN_LOCATION + " ".join(args))

def mailman_list_lists():
    return mailman("list_lists")

def mailman_add_member(mlist, member):
    return mailman("add_members", mlist, indata=member)

def main():
    options, args = parse_options()
    #print 'options:', options
    #print 'args:', args

    if options.list:
        mmlist_out, mmlist_err = mmlist_list_lists()
        mailman_out, mailman_err = mailman_list_lists()

        out = ''
        if not mmlist_err and not mailman_err:
            print mmlist_out, mailman_out
        elif not mailman_err:
            print 'Mailman Error:'
            print mailman_err
        elif not mmlist_err:
            print 'mmlist Error:'
            print mmlist_err
        else:
            print mmlist_err, mailman_err
    elif options.expansion != None:
        email = options.expansion
        full_email = options.expansion
        if '@' not in email:
            full_email = email + '@hkn.eecs.berkeley.edu'

        rflag = ""
        if options.recursive:
            rflag = "-r "

        #print email, full_email
        mmlist_proc = sp.Popen('python ' + MMLIST_LOCATION + 'mmlist.py ' + rflag + '-b ' + email, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
        mmlist_out = mmlist_proc.stdout.read()
        mmlist_err = mmlist_proc.stderr.read()

        mailman_proc = sp.Popen('python ' + MAILMAN_LOCATION + 'find_member ' + full_email, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
        mailman_out = mailman_proc.stdout
        mailman_err = mailman_proc.stderr.read()

        out = ''
        if not mmlist_err and not mailman_err:
            current_line = mailman_out.readline()
            while current_line:
                if full_email not in current_line:
                    out += current_line.strip(' ')
                current_line = mailman_out.readline()
            print mmlist_out, out
        elif not mailman_err:
            print 'Mailman Error:'
            print mailman_err
        elif not mmlist_err:
            print 'mmlist Error:'
            print mmlist_err
        else:
            print mmlist_err, mailman_err


    else:
        print 'show options'


if __name__ == "__main__":
    main()
