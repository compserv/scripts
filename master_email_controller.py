#!/usr/bin/env python

#TODO: write these two functions

# options needed:
# -l something to list all the mailing lists
# -b (list all lists a given member is on)

import subprocess as sp
from optparse import OptionParser

MMLIST_LOCATION = '/home/hkn/compserv/scripts/'
MAILMAN_LOCATION = '/usr/lib/mailman/bin/'

def parse_options():
    parser = OptionParser()
    parser.add_option('-l', '--list',  action='store_true', dest='list', default=False,
            help='list all mailing lists')

    parser.add_option('-b', dest='expansion', metavar='expansion',
            help='reverse expand expansion, find targets expansion belongs to')

    options, args = parser.parse_args()
    return (options, args)

def main():
    options, args = parse_options()
    #print 'options:', options
    #print 'args:', args

    if options.list:
        print 'there is the list option'
        print options.list
    elif options.expansion != None:
        email = options.expansion
        full_email = options.expansion
        if '@' not in email:
            full_email = email + '@hkn.eecs.berkeley.edu'

        #print email, full_email
        mmlist_proc = sp.Popen('python ' + MMLIST_LOCATION + 'mmlist.py -b ' + email, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
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
