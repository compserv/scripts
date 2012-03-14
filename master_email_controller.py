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
    global parser
    parser = OptionParser()
    parser.add_option('-l', '--list',  action='store_true', dest='list', default=False,
            help='list all mailing lists')

    parser.add_option('-r', '--recursive',  action='store_true', dest='recursive', default=False,
            help='make -b act recursively')

    parser.add_option('-b', dest='expansion', metavar='expansion',
            help='list mailing lists that the specified address (either an ' +
            'individual\'s email or another list) is on')

    parser.add_option('-e', dest='target', metavar='target',
            help='list members of a mailing list')

    parser.add_option('-i', dest="to_insert", metavar="email entry", nargs=2,
            help="insert email into mailing list entry")
    
    parser.add_option('-d', dest="to_delete", metavar="email entry", nargs=2,
            help="delete email from mailing list entry")

    options, args = parser.parse_args()
    return (options, args)

def main():
    options, args = parse_options()
    #print 'options:', options
    #print 'args:', args

    if options.list:
        mmlist_lists = mmlist.list_lists()
        mailman_lists = mailman.list_lists()
        for mlist in mmlist_lists:
            print mlist
        for mlist in mailman_lists:
            print mlist
    elif options.expansion != None:
        email = options.expansion
        full_email = options.expansion
        if '@' not in email:
            full_email = email + '@hkn.eecs.berkeley.edu'

        mmlist_lists = mmlist.find_member(email, options.recursive)
        mailman_lists = mailman.find_member(full_email)

        for mlist in mmlist_lists:
            print mlist
        for mlist in mailman_lists:
            print mlist
    elif options.target != None:
        mmlist_members = mmlist.expand_list(options.target, options.recursive)
        mailman_members = mailman.expand_list(options.target)
        for addr in mmlist_members:
            print addr
        for addr in mailman_members:
            print addr
    elif options.to_insert != None:
        email, mlist = options.to_insert
        mmlist_err = ""
        try:
            mmlist.add_member(email, mlist)
            return
        except Exception as expt:
            mmlist_err = "\n".join(expt.args)
        try:
            mailman.add_member(email, mlist)
            return
        except Exception as expt:
            raise Exception("Could not insert into " + mlist + "\n mmlist:\n" + 
                mmlist_err + "\n\nMailman:\n" + "\n".join(expt.args))
    elif options.to_delete != None:
        email, mlist = options.to_delete
    else:
        print parser.print_help()


# Helper functions!

def runproc(cmd, indata=None):
    proc = sp.Popen('python ' + cmd, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
    if indata is not None:
        proc.communicate(input=indata)
    out = proc.stdout.read()
    err = proc.stderr.read()
    return out, err

class mmlist:
    @classmethod
    def invoke(cls, *args):
        result = runproc(MMLIST_LOCATION + "mmlist.py " + " ".join(args))
        if result[1]:
            raise Exception("mmlist error: " + result[1])
        return result[0] 

    @classmethod
    def list_lists(cls):
        return [x for x in cls.invoke("-l").split("\n") if x]

    @classmethod
    def add_member(cls, mlist, member):
        return cls.invoke("-i", member, mlist)

    @classmethod
    def find_member(cls, member, recursive):
        if recursive:
            result = cls.invoke("--no-error", "-rb", member)
        else:
            result = cls.invoke("--no-error", "-b", member)
        return [x for x in result.split("\n") if x]

    @classmethod
    def expand_list(cls, mlist, recursive):
        if recursive:
            result = cls.invoke("--no-error", "-re", mlist)
        else:
            result = cls.invoke("--no-error", "-e", mlist)
        return [x for x in result.split("\n") if x]

class mailman:
    @classmethod
    def invoke(cls, *args, **keywords):
        if "indata" in keywords.keys():
            result = runproc(MAILMAN_LOCATION + " ".join(args), indata = keywords["indata"])
        else:
            result = runproc(MAILMAN_LOCATION + " ".join(args))
        if result[1]:
            raise Exception("Mailman error: " + result[1])
        else:
            return result[0] 

    @classmethod
    def list_lists(cls):
        return [x for x in cls.invoke("list_lists", "-b").split("\n") if x]

    @classmethod
    def add_member(cls, mlist, member):
        return cls.invoke("add_members", "--welcome-msg=n", "--admin-notify=n",
            "n", "-r", "-",  mlist, indata=member)

    @classmethod
    def find_member(cls, member):
        result = [x.strip() for x in cls.invoke("find_member", "^"+member+"$").split("\n") if x]
        if len(result) > 0:
            return result[1:]
        else:
            return []

    @classmethod
    def expand_list(cls, mlist):
        try:
            result = cls.invoke("list_members", mlist)
        except Exception as expt:
            if "No such list:" in expt.args[0]:
                return []
            else:
                raise Exception(expt.args[0])
        return [x for x in result.split("\n") if x]


if __name__ == "__main__":
    main()
