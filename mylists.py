#! /usr/bin/env python
import os
import mmlist
import sys
from optparse import OptionParser
from subprocess import Popen, PIPE

SCRIPT_PATH = "/home/hkn/compserv/scripts/mmlist.py "

def run_mmlist(options, recursive):
    recurseOpt = "-r " if recursive else ""
    cmd = SCRIPT_PATH + recurseOpt + options
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.stdout
    results = [line[:-1] for line in output.readlines()]

    return results

def expand_user(login, recursive):
    options = "-b " + login
    return run_mmlist(options, recursive)

def expand_list(list, recursive):
    options = "-e " + list
    return run_mmlist(options, recursive)

def list_lists(list):
    options = "-l"
    return run_mmlist(options, False)

def parse_options(argv):
    parser = OptionParser()
    parser.add_option("-l", action="store_true", dest="list", default=False,
            help="list all the mailing lists")
    parser.add_option("-r", action="store_true", dest="recursive",
            default=False,
            help="make things recursive, e.g. show comms, indrel, and indrel-cmembers instead of just indrel-cmembers")
    parser.add_option("-e", dest="target", metavar="target",
            help="show the people/other lists on a mailing list")
    parser.add_option("-b", dest="expansion", metavar="expansion",
            help="show the mailing lists a person is on")

    options, args = parser.parse_args(argv)
    return (options, args)

def main():
    if len(sys.argv) == 1:
	argv = ["-b", os.getlogin()]
    else:
	argv = sys.argv[1:]

    options, args = parse_options(argv)
    if len(args) == 0:
	args = [os.getlogin()]

    output = []
    if options.list:
	output = list_lists(args[0])
    elif options.target:
	output = expand_list(args[0], options.recursive)
    elif options.expansion:
	output = expand_user(args[0], options.recursive)

    for result in output:
	print result

if __name__ == "__main__":
    main()
