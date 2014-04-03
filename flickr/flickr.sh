#!/bin/bash
#
# flickr cron daily
# The script to backup Bridge's photos to Flickr.

cd /home/hkn/compserv/scripts/flickr
./FLICKRENV/bin/python uploader.py | mail -s "cron output" josephhui@hkn.eecs.berkeley.edu
