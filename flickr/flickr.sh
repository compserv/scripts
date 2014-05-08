#!/bin/bash
#
# flickr cron daily
# The script to backup Bridge's photos to Flickr.

cd /home/hkn/compserv/scripts/flickr
chown -R hkn:bridge /hkn/bridge/flickr/pictures
chmod -R 775 /hkn/bridge/flickr/pictures
./FLICKRENV/bin/python uploader.py
