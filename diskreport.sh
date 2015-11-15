#!/bin/bash

tempfile=`mktemp /tmp/diskreport.XXXXXX` || exit 1
date=`date`
FROM="root@hkn.eecs.berkeley.edu"
TO="compserv@hkn.moe"
echo "From: $FROM">$tempfile
echo "To: $TO">>$tempfile
echo "Reply-To: $TO">>$tempfile
echo "Subject: Disk Usage Report for" $date>>$tempfile
echo>>$tempfile

echo "Disk Usage Report for" $date>>$tempfile
echo>>$tempfile
echo "====df output====">>$tempfile
df -h>>$tempfile
echo>>$tempfile
echo "====Largest Home Directories====">>$tempfile
du -s /home/* --exclude=yearbook 2>/dev/null| sort -nr | head -n15 | cut -f 2- | while read a; do du -hs $a 2>/dev/null; done>>$tempfile
#du /home/* -s 2>/dev/null| sort -nr | head -n15>>$tempfile
echo>>$tempfile

cat $tempfile |/usr/sbin/sendmail -t
rm $tempfile
