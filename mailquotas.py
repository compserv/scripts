#!/usr/bin/python

import os
from os.path import getsize, join
import sys

threshold = 950*2*1024*1024 #This is 95% of the mail quota of 2GB

def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0

def main():
    hosers = 0
    for file in os.listdir('/var/mail'):
        size = 0
        try:
            size = getsize(join('/var/mail/', file))
        except:
            print file + " was unreadable"
        if size > threshold:
            print file + " is using %s" % sizeof_fmt(size)
            hosers += 1
    sys.exit(hosers)

if __name__ == "__main__":
    main()

