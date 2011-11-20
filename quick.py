#!/usr/bin/env python

import os

f = open('diff.txt')

for line in f.readlines():
    login, comm = line.split()[-2:]

    os.system('sudo ./hknmod.py -u -l %s -c %s' % (login, comm))
