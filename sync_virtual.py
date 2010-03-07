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
# TODO: SEARCH IN ALIASES file as well

import os
import sys
from optparse import OptionParser

MAILLISTS_DIR = "/home/hkn/compserv/new-maillists"
VIRTUAL = "/home/hkn/compserv/virtual.sample"
ALIASES = "/home/hkn/compserv/aliases.sample"

def error_exit(str):
    print "[ERROR] %s" % str
    sys.exit(1)

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
        else:
            entries.append(file)

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
        error_exit("Following entry had no expansions: %s" % entry)

    return ({entry: addresses}, aliases)

def read_ruleset(ruleset_path):
    """
    ruleset - full path to the ruleset entry
    
    return - dictionary
    """

    ruleset = ruleset_path
    f = open(ruleset_path)
    virtual = {}

    lines = clean_lines(f.readlines())
    for line in lines:
        target = line.split()[0]
        # TODO REDO BASED ON "," NOT SPACE
        expansions = "".join(line.split()[1:])
        expansions_list = [expansion for expansion in
                expansions.split(",") if len(expansion) > 0]
        virtual[target] = expansions_list

    return (virtual, {})

def read_aliases_ruleset(aliases_ruleset_path):
    """
    ruleset
    """
    ### TODO

    aliases_ruleset = aliases_ruleset_path
    f = open(aliases_ruleset_path)
    aliases = {}

    lines = clean_lines(f.readlines())
    for line in lines:
        target = line.split(":")[0].strip()
        expansions = ":".join(line.split(":")[1:])
        expansions_list = [expansion.strip() for expansion in
                expansions.split(",") if len(expansion.strip()) > 0]
        aliases[target] = expansions_list

    # TODO
    return ({}, aliases)

def read_directory(directory_path):
    """
    directory - full path to the directory

    return - dictionary
    """

    directory = os.path.basename(directory_path)
    entries, rulesets, aliases_rulesets, addons, directories = list_files(directory_path)

    if not entries and not directories:
        error_exit("Following directory had no expansions: %s" % directory)

    return ({directory: entries + directories}, {})


def read_addon(addon_path, dir_virtual):
    """
    addon - full path to the addon
    """

    addon = os.path.basename(addon_path)[1:]
    addresses = []
    
    f = open(addon_path)
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
        error_exit("Following addon had no expansions: %s" % addon)

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
    parser.add_option("-e", dest="target", metavar="target",
            help="expand target")
    parser.add_option("-b", dest="expansion", metavar="expansion",
            help="reverse expand expansion; find targets expansion belongs to")
    parser.add_option("-a", action="store_true", dest="aliases", default=False,
            help="do given action for the aliases file")

    options, args = parser.parse_args()
    return (options, args)

def list_targets(table):
    # table = aliases or virtual table
    to_print = table.keys()
    to_print.sort()
    print "\n".join(to_print)

def expand(to_lookup, recursive, table):
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
        print "\n".join(to_print)
    else:
        error_exit("Could not find target: %s" % to_lookup)

def reverse_expand(to_lookup, recursive, table):
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
        print "\n".join(to_print)
    else:
        error_exit("Could not find expansion: %s" % to_lookup)

def main():
    global MAILLISTS_DIR
    virtual, aliases = fill_table(MAILLISTS_DIR)

    for target in virtual.keys():
        if not virtual[target]:
            error_exit("Following target has no expansion: %s" % target)

    for target in aliases.keys():
        if not aliases[target]:
            error_exit("Following target has no expansion: %s" % target)

    options, args = parse_options()
    if options.list:
        table = aliases if options.aliases else virtual
        list_targets(table)
    elif options.target != None:
        table = aliases if options.aliases else virtual
        expand(options.target, options.recursive, table)
    elif options.expansion != None:
        table = aliases if options.aliases else virtual
        reverse_expand(options.expansion, options.recursive, table)
    else:
        global VIRTUAL
        virtual_file = open(VIRTUAL, "w")

        global ALIASES
        aliases_file = open(ALIASES, "w")

        for target in virtual.keys():
            expansions = ", ".join(virtual[target])
            virtual_file.write("%s\t\t\t%s\n" % (target, expansions))

        for target in aliases.keys():
            expansions = ", ".join(aliases[target])
            aliases_file.write("%s:\t\t\t%s\n" % (target, expansions))

if __name__ == "__main__":
    main()
