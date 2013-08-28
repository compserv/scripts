#!/usr/bin/env python

# TODO: CLEAN UP
#
# 2 types of files
# * ruleset file - has body just like virtual file ( start with @), comments are
# not copied over
# * entry file - one username per line
# * addon file - specify directory and it goes through the directory looking for
# all entries that end in the name of the file, and list them as expansions of
# the addon
# * directory - includes the non-ruleset non-addon files inside the directory as the expansions
# * aliases_ruleset - @@

# expansion is dest and people it goes to

# TODO: MENTION ALL OPTIONS ARE MUTUALLY EXCLUSIVE
# TODO: SEARCH IN ALIASES_OUTPUT file as well

import fcntl
import os
import subprocess
import sys
import shutil
from optparse import OptionParser

SCRIPT_HOME = "/home/hkn/compserv/mmlist"
SCRIPT_LOCK = os.path.join(SCRIPT_HOME, "lock")

MAILLISTS_DIR = os.path.join(SCRIPT_HOME, "maillists")
CURRENT_MLISTS_DIR = os.path.join(MAILLISTS_DIR, 'current')
PREVIOUS_MLISTS_DIR = os.path.join(MAILLISTS_DIR, 'previous')
VIRTUAL_OUTPUT = os.path.join(SCRIPT_HOME, "virtual.sample")
ALIASES_OUTPUT = os.path.join(SCRIPT_HOME, "aliases.sample")

ACTUAL_VIRTUAL = '/etc/postfix/virtual'
ACTUAL_ALIASES = '/etc/aliases'

ENTRIES_PATH = set([])

class NoExpansionException(Exception): pass

def script_exit(error_code):
    try:
        global SCRIPT_LOCK
        f = open(SCRIPT_LOCK)
        pid = int(f.readline())
        f.close()
        if pid == os.getpid():
            try:
                os.remove(SCRIPT_LOCK)
            except:
                print("[CRITICAL ERROR] Couldn't remove lock file belonging " +
                "to this process.")
    except:
        pass


def error_exit(str):
    script_exit(1)
    raise Exception(str)

def clean_lines(lines):
    """
    lines - List of strings; each string is a line.

    Removes commented lines starting with # or has just whitespace
    """
    new_lines = []
    for line in lines:
        cleaned_line = line.strip()
        if len(cleaned_line) > 0 and cleaned_line[0] != "#":
            new_lines.append(cleaned_line)

    return new_lines

def list_files(dirpath):
    """
    Reads the list of files stored in the dirpath and returns a tuple:
    (entries, rulesets, addons, directories).
    """
    global ENTRIES_PATH
    files = os.listdir(dirpath)
    entries = []
    rulesets = []
    aliases_rulesets = []
    addons = []
    directories = []
    for file in files:
        if file[0:2] == "@@":
            aliases_rulesets.append(file)
        elif file[0] == "@":
            rulesets.append(file)
        elif file[0] == "\\":
            addons.append(file)
        elif os.path.isdir(os.path.join(dirpath, file)):
            directories.append(file)
        elif file[-3:] == "swp":
            continue
        else:
            entries.append(file)
            ENTRIES_PATH.add(os.path.join(dirpath, file))

    return (entries, rulesets, aliases_rulesets, addons, directories)

def read_entry(entry_path):
    """
    entry - full path to the entry file

    return - dictionary
    """
    def update_aliases(target, expansion, aliases):
        if target in aliases.keys():
            aliases[target].append(expansion)
        else:
            aliases[target] = [expansion]


    entry = os.path.basename(entry_path)
    f = open(entry_path)
    try:
        fcntl.lockf(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
    except IOError:
        error_exit("Cannot lock file: %s" % entry_path)

    addresses = []
    aliases = {}

    lines = clean_lines(f.readlines())
    for line in lines:
        if line[0] != "@":
            addresses.append(line)
        else:
            aliases_target = entry + "-aliases"
            expansion = line[1:].strip()
            update_aliases(aliases_target, expansion, aliases)
            addresses.append(aliases_target)

    # If entry file is empty, print error and exit
    if not addresses:
        raise NoExpansionException("Following entry had no expansions: %s" % entry)

    fcntl.lockf(f.fileno(), fcntl.LOCK_UN)
    f.close()

    return ({entry: addresses}, aliases)

def read_ruleset(ruleset_path):
    """
    ruleset - full path to the ruleset entry

    return - dictionary
    """

    ruleset = ruleset_path
    f = open(ruleset_path)
    try:
        fcntl.lockf(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
    except IOError:
        error_exit("Cannot lock file: %s" % entry_path)

    virtual = {}

    lines = clean_lines(f.readlines())
    for line in lines:
        target = line.split()[0]
        # TODO REDO BASED ON "," NOT SPACE
        expansions = "".join(line.split()[1:])
        expansions_list = [expansion for expansion in
                expansions.split(",") if len(expansion) > 0]
        virtual[target] = expansions_list

    fcntl.lockf(f.fileno(), fcntl.LOCK_UN)
    f.close()

    return (virtual, {})

def read_aliases_ruleset(aliases_ruleset_path):
    """
    ruleset
    """
    ### TODO

    aliases_ruleset = aliases_ruleset_path
    f = open(aliases_ruleset_path)
    try:
        fcntl.lockf(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
    except IOError:
        error_exit("Cannot lock file: %s" % entry_path)

    aliases = {}

    lines = clean_lines(f.readlines())
    for line in lines:
        target = line.split(":")[0].strip()
        expansions = ":".join(line.split(":")[1:])
        expansions_list = [expansion.strip() for expansion in
                expansions.split(",") if len(expansion.strip()) > 0]
        aliases[target] = expansions_list

    fcntl.lockf(f.fileno(), fcntl.LOCK_UN)
    f.close()

    return ({}, aliases)

def read_directory(directory_path):
    """
    directory - full path to the directory

    return - dictionary
    """

    directory = os.path.basename(directory_path)
    entries, rulesets, aliases_rulesets, addons, directories = list_files(directory_path)

    if not entries and not directories:
        raise NoExpansionException("Following directory had no expansions: %s" % directory)

    return ({directory: entries + directories}, {})


def read_addon(addon_path, dir_virtual):
    """
    addon - full path to the addon
    """

    addon = os.path.basename(addon_path)[1:]
    addresses = []

    f = open(addon_path)
    try:
        fcntl.lockf(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
    except IOError:
        error_exit("Cannot lock file: %s" % entry_path)

    lines = clean_lines(f.readlines())
    for line in lines:
        if line[0] == "@":
            to_search = line[1:].strip()
            possible_expansions = dir_virtual[to_search].keys()
            for possible_expansion in possible_expansions:
                if possible_expansion.find(addon) != -1:
                    addresses.append(possible_expansion)
        else:
            addresses.append(line)

    if not addresses:
        raise NoExpansionException("Following addon had no expansions: %s" % addon)

    fcntl.lockf(f.fileno(), fcntl.LOCK_UN)
    f.close()

    return ({addon: addresses}, {})

def fill_table(dirpath):
    """
    Opens the given dirpath and returns an virtual table containing all the
    virtual form the entries, rulesets, addons, and directories in that
    dirpath. The given dirpath has to be the full path to the directory.
    """

    #global MAILLISTS_DIR
    entries, rulesets, aliases_rulesets, addons, directories = list_files(dirpath)

    virtual = {}
    dir_virtual = {}
    aliases = {}

    # vrules = rules for the virtual file
    # arules = rules for the aliases file
    for entry in entries:
        vrules, arules = read_entry(os.path.join(dirpath, entry))
        virtual.update(vrules)
        aliases.update(arules)
    for ruleset in rulesets:
        vrules, arules = read_ruleset(os.path.join(dirpath, ruleset))
        virtual.update(vrules)
        aliases.update(arules)
    for aliases_ruleset in aliases_rulesets:
        vrules, arules = read_aliases_ruleset(os.path.join(dirpath,
            aliases_ruleset))
        virtual.update(vrules)
        aliases.update(arules)
    for directory in directories:
        vrules, arules = read_directory(os.path.join(dirpath, directory))
        dir_vrules, dir_arules = fill_table(os.path.join(dirpath, directory))
        dir_virtual[directory] = dir_vrules
        virtual.update(vrules)
        aliases.update(arules)
        virtual.update(dir_virtual[directory])
        aliases.update(dir_arules)
    for addon in addons:
        vrules, arules = read_addon(os.path.join(dirpath, addon), dir_virtual)
        virtual.update(vrules)
        aliases.update(arules)

    return virtual, aliases

def parse_options():
    parser = OptionParser()
    parser.add_option("-l", action="store_true", dest="list", default=False,
            help="list all mailing list targets")
    parser.add_option("-r", action="store_true", dest="recursive",
            default=False,
            help="make expansion or reverse expansion recursive")
    parser.add_option("--no-error", action="store_true", dest="no_error",
            default=False, help="if a target cannot be found during expansion" +
            " or reverse expansion, exit quietly instead of erroring out")
    parser.add_option("--diff", action="store_true", dest="diff",
            default=False, help="Find changes that would be made if mmlist.py" +
            " -z is run")
    parser.add_option("-e", dest="target", metavar="target",
            help="expand target")
    parser.add_option("-b", dest="expansion", metavar="expansion",
            help="reverse expand expansion; find targets expansion belongs to")
    parser.add_option("-a", action="store_true", dest="aliases", default=False,
            help="do given action for the aliases file")
    parser.add_option("-i", dest="to_insert", metavar="email entry", nargs=2,
            help="inserts the email to the given target. Works only with " +
            "virtual file.")
    parser.add_option("-d", dest="to_delete", metavar="email entry", nargs=2,
            help="deletes the email from the given target. This doesn't " +
            "actually delete the entry but only comments it out. Works only " +
            "with virtual file.")
    parser.add_option("-f", dest="mlist_dir", metavar="directory",
            help="Indicate the directory under which mailing lists are " +
            "specified, default is maillists")
    parser.add_option("-z", action="store_true", dest="real_sync",
            default=False, help="syncs directly to the actual file instead" +
            "of syncing to the test aliases and virtual file.")
    parser.add_option('-c', action='store_true', dest='clean',
            default=False, help='cleans the mmlist lock file.')
    parser.add_option('-w', dest='to_wipe', metavar='mailing list',
            help="wipe the mailing list given (must be entry type)")
    parser.add_option("--wipe-current", action="store_true", dest="wipe_all",
            default=False, help="wipe all the current-* mailing lists, after " +
            "copying contents to previous-*")

    options, args = parser.parse_args()
    return (options, args)

def list_targets(table):
    # table = aliases or virtual table
    to_print = table.keys()
    to_print.sort()
    print "\n".join(to_print)

def expand(to_lookup, recursive, table, no_error=False):
    # table = aliases or virtual table list
    table_keys = table.keys()

    def shallow_expand(target):
        if target in table_keys:
            return table[target]
        else:
            return []

    def recursive_expand(target):
        expansions = shallow_expand(target)
        unflattened = [recursive_expand(expansion) for expansion in expansions]
        flattened = reduce(list.__add__, unflattened) if unflattened else []
        return flattened + expansions

    if to_lookup in table_keys:
        if recursive:
            to_print = recursive_expand(to_lookup)
            to_print = list(set(to_print))
        else:
            to_print = shallow_expand(to_lookup)
        to_print.sort()
        return to_print
    else:
        if no_error:
            return []
        else:
            error_exit("Could not find target: %s" % to_lookup)

def reverse_expand(to_lookup, recursive, table, no_error=False):
    # table = aliases or virtual table list
    all_expansions = reduce(list.__add__, table.values()) if table.values() else []
    table_items = table.items()

    def shallow_reverse_expand(expansion):
        if expansion in all_expansions:
            targets = [target for target, expansions in table_items
                    if expansion in expansions]
            return targets
        else:
            return []

    def recursive_reverse_expand(expansion):
        targets = shallow_reverse_expand(expansion)
        unflattened = [recursive_reverse_expand(target) for target in targets]
        flattened = reduce(list.__add__, unflattened) if unflattened else []
        return flattened + targets

    if to_lookup in all_expansions:
        if recursive:
            to_print = recursive_reverse_expand(to_lookup)
            to_print = list(set(to_print))
        else:
            to_print = shallow_reverse_expand(to_lookup)
        to_print.sort()
        return to_print
    else:
        if no_error:
            return []
        else:
            error_exit("Could not find expansion: %s" % to_lookup)

def insert_email(email, entry, no_error=False):
    global ENTRIES_PATH
    email = email.strip()
    entry_path = ""

    for path in ENTRIES_PATH:
        if entry == os.path.basename(path):
            entry_path = path

    if entry_path == "":
        if no_error:
            return
        error_exit("Could not find entry file: %s" % entry)

    f = open(entry_path, 'a+')
    lines = f.readlines()
    for line in lines:
        if email == line.strip():
            if no_error:
                return
            error_exit("Following email %s already exists in entry %s" % (email, entry))

    last_line = lines[len(lines)-1]
    if last_line[len(last_line)-1] != '\n':
        # If last character isn't a newline
        f.write('\n')
    f.write(email + '\n')
    f.close()

def delete_email(email, entry, no_error=False):
    global ENTRIES_PATH
    email = email.strip()
    entry_path = ""

    for path in ENTRIES_PATH:
        if entry == os.path.basename(path):
            entry_path = path

    if entry_path == "":
        if no_error:
            return
        error_exit("Could not find entry file: %s" % entry)

    f = open(entry_path, 'r+')
    lines = f.readlines()
    email_index = -1
    for line in lines:
        if email == line.strip():
            email_index = lines.index(line)
    if email_index == -1:
        if no_error:
            f.close()
            return
        error_exit("Following email doesn't exists in entry: %s" % email)

    lines[email_index] = '#' + lines[email_index]
    f.seek(os.SEEK_SET)
    f.writelines(lines)
    f.close()

def wipe_all_current_mlists():
    lists = os.listdir(CURRENT_MLISTS_DIR)
    for list in lists:
        #if list != 'current-committees': Moved current-committees out of this
        # directory
        move_current_to_previous(list)
        wipe_current_mlist(list)

def wipe_current_mlist(mlist):
    mlist_path = os.path.join(CURRENT_MLISTS_DIR, mlist)

    if not os.path.isfile(mlist_path):
        raise Exception("Could not find entry file: %s" % mlist)

    f = open(mlist_path, 'w')
    print >>f, 'devnull'
    f.close()

def move_current_to_previous(mlist):
    mlist_path = os.path.join(CURRENT_MLISTS_DIR, mlist)
    previous_name = "previous-" + "-".join(mlist.split("-")[1:])
    new_path = os.path.join(PREVIOUS_MLISTS_DIR, previous_name)
    if not os.path.isfile(mlist_path):
        raise Exception("Could not find entry file: %s" % mlist)

    shutil.copy(mlist_path, new_path)


def init():
    # If there is another instance of the script running, it will have created
    # a lock file with the pid of the instance in it. If we find this file,
    # error out. There should not be more than one instance of mmlist running
    # at one time.
    global SCRIPT_LOCK
    try:
        fd = os.open(SCRIPT_LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0640)
    except Exception:
        error_exit("Script lock file present. Another instance of the script "
                + "is probably running.")
    os.write(fd, str(os.getpid()))
    os.close(fd)

    global MAILLISTS_DIR
    if not os.path.isdir(MAILLISTS_DIR):
        error_exit("MAILLISTS_DIR does not exists.")

    virtual, aliases = fill_table(MAILLISTS_DIR)

    for target in virtual.keys():
        if not virtual[target]:
            raise NoExpansionException("Following target has no expansion: %s" % target)

    for target in aliases.keys():
        if not aliases[target]:
            raise NoExpansionException("Following target has no expansion: %s" % target)

    return virtual, aliases

def main():
    global VIRTUAL_OUTPUT, ALIASES_OUTPUT, ACTUAL_VIRTUAL, ACTUAL_ALIASES
    options, args = parse_options()

    if options.clean:
        os.remove(SCRIPT_LOCK)
        script_exit(0)
        return
    if options.mlist_dir is not None:
        global MAILLISTS_DIR
        global CURRENT_MLISTS_DIR
        global PREVIOUS_MLISTS_DIR
        MAILLISTS_DIR = os.path.join(SCRIPT_HOME, options.mlist_dir)
        CURRENT_MLISTS_DIR = os.path.join(MAILLISTS_DIR, 'current')
        PREVIOUS_MLISTS_DIR = os.path.join(MAILLISTS_DIR, 'previous')

    # I'm gonna go ahead and hardcode this bit in -rkandasamy
    if options.real_sync:
        p1 = subprocess.Popen(["/home/hkn/compserv/scripts/mailman_aliases.sh", os.path.join(MAILLISTS_DIR, '@@mailman')])
        p1.wait()


    virtual, aliases = init()
    if options.list:
        table = aliases if options.aliases else virtual
        list_targets(table)
    elif options.target is not None:
        table = aliases if options.aliases else virtual
        to_print = expand(options.target, options.recursive, table, options.no_error)
        if len(to_print) > 0:
            print "\n".join(to_print)
    elif options.expansion is not None:
        table = aliases if options.aliases else virtual
        to_print = reverse_expand(options.expansion, options.recursive, table, options.no_error)
        if len(to_print) > 0:
            print "\n".join(to_print)
    elif options.to_insert is not None:
        email, entry = options.to_insert
        insert_email(email, entry, options.no_error)
    elif options.to_delete is not None:
        email, entry = options.to_delete
        delete_email(email, entry, options.no_error)
    elif options.to_wipe is not None:
        mlist = options.to_wipe
        wipe_mlist(mlist)
    elif options.wipe_all:
        wipe_all_current_mlists()
    elif options.real_sync:
        try:
            actual_virtual = open(ACTUAL_VIRTUAL, 'w')

            for target in virtual.keys():
                expansions = ", ".join(virtual[target])
                actual_virtual.write("%s\t\t\t%s\n" % (target, expansions))

            actual_aliases = open(ACTUAL_ALIASES, 'w')

            for target in aliases.keys():
                expansions = ", ".join(aliases[target])
                actual_aliases.write("%s:\t\t\t%s\n" % (target, expansions))

            actual_virtual.close()
            actual_aliases.close()

            #print "postmap " + ACTUAL_VIRTUAL
            #print "newaliases"
            if subprocess.call(["/usr/sbin/postmap", ACTUAL_VIRTUAL]) != 0: raise Exception
            if subprocess.call(["/usr/bin/newaliases"]) != 0: raise Exception
        except:
            error_exit("Could not sync with actual virtual and aliases files." +
            "You probably didn't use sudo.")

    else:
        virtual_file = open(VIRTUAL_OUTPUT, "w")

        aliases_file = open(ALIASES_OUTPUT, "w")

        for target in virtual.keys():
            expansions = ", ".join(virtual[target])
            virtual_file.write("%s\t\t\t%s\n" % (target, expansions))

        for target in aliases.keys():
            expansions = ", ".join(aliases[target])
            aliases_file.write("%s:\t\t\t%s\n" % (target, expansions))

        virtual_file.close()
        aliases_file.close()

    if options.diff:
        p1 = subprocess.Popen(["/usr/bin/diff", ACTUAL_ALIASES, ALIASES_OUTPUT], stdout=subprocess.PIPE)
        p1.wait()
        print p1.communicate()[0]
        p2 = subprocess.Popen(["/usr/bin/diff", ACTUAL_VIRTUAL, VIRTUAL_OUTPUT], stdout=subprocess.PIPE)
        p2.wait()
        print p2.communicate()[0]


    script_exit(0)

if __name__ == "__main__":
    main()
