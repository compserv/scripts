#!/bin/bash

tempfile=`mktemp /tmp/diskreport.XXXXXX` || exit 1
date=`date`
FROM="root@hkn.eecs.berkeley.edu"
TO="ops@hkn.eecs.berkeley.edu"
echo "From: $FROM">$tempfile
echo "To: $TO">>$tempfile
echo "Reply-To: $TO">>$tempfile
echo "Subject: Mail Quota Report for" $date>>$tempfile

echo "Large mail spools found. Please look into these and contact the offenders ASAP.">>$tempfile
echo>>$tempfile

/usr/bin/python /home/hkn/compserv/scripts/mailquotas.py>>$tempfile
hosers=$?

if [ $hosers -ne 0 ]; then
    cat $tempfile|/usr/sbin/sendmail -t
fi
rm $tempfile
