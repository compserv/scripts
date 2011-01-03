#!/bin/bash

tempfile=`mktemp /tmp/diskreport.XXXXXX` || exit 1
date=`date`
FROM="root@hkn.eecs.berkeley.edu"
TO="ops@hkn.eecs.berkeley.edu"
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

echo "====Largest Mail Spools====">>$tempfile
names=`ls -1hsS /var/mail|tail -n+2|head -n15|gawk '{print $2;}'`
for name in ${names[@]}
do
  echo $name '('`ls -1hsS /var/mail | /bin/grep -w $name | gawk '{print $1;}'`'):' `python /home/hkn/compserv/scripts/mmlist.py -b $name | tr '\n' ' '` >> $tempfile
done

cat $tempfile |/usr/sbin/sendmail -t
rm $tempfile
