#!/bin/bash

# The HKN database backup script.
# Written by ibrahima, sp10 compserv. See the git repo for commit history.
# This script must be run as root, because root has automatic authorization
# for postgres without having to enter the password.

MMMYY=`date +"%b%y"`
MONTH=`date +"%b"`

DATE=`date +"%Y-%m-%d"`
TIME=`date +"%H%M"`
BACKUPHOME=/home/hkn/compserv/dbbackups
BACKUPPATH=$BACKUPHOME/$MMMYY
DBLIST=(hkn_rails_production postgres redmine wikidb)
if [ ! -d $BACKUPPATH ]; then
    mkdir $BACKUPPATH
fi

cd $BACKUPPATH
for DB in "${DBLIST[@]}"; do #Dump each database in the list
    #Dump the current database into a file
    echo "Dumping $DB"
    pg_dump -U postgres $DB > $DB-$DATE-$TIME.sql

    echo "Compressing archives of $DB"
    pbzip2 -f $DB-$DATE-$TIME.sql
done

echo "Compressing databases into one file"
GLACIERFILE=$BACKUPHOME/glacier-temp.tar
IDSFILE=$BACKUPPATH/glacier-$MMMYY-ids

#Compress all the dbs into one file
cd $BACKUPHOME
tar cvf $GLACIERFILE $MMMYY

#Run Python script to upload to Glacier
echo "Uploading all databases to Glacier"
cd /home/hkn/compserv/scripts/glacier
source ENV/bin/activate
#Save the archive ID to file
python glacier.py $GLACIERFILE >> $IDSFILE

#Delete backups from 7 months ago
OLD_MMMYY=`date --date='-7 month' +"%b%y"`
OLD_BACKUPPATH=$BACKUPHOME/$OLD_MMMYY
OLD_IDS_FILE=$OLD_BACKUPPATH/glacier-$OLD_MMMYY-ids
python glacier.py --delete $GLACIERFILE >> $IDSFILE

deactivate

