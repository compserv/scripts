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
DBLIST=(hkn_rails_production gallery3 postgres redmine wikidb)
if [ ! -d $BACKUPPATH ]; then
    mkdir $BACKUPPATH
fi
if [ ! -d $BACKUPHOME/latest ]; then
    mkdir $BACKUPHOME/latest
fi
cd $BACKUPPATH
for DB in "${DBLIST[@]}"; do #Dump each database in the list
    MONTHLYARCH=$DB-$MMMYY
    if [ -f $MONTHLYARCH.tar.bz2 ]; then #If we already made an archive of monthly backups, extract it.
	tar -xjf $MONTHLYARCH.tar.bz2
    else
	mkdir $MONTHLYARCH
    fi
    #Dump the current database into a file
    echo "Dumping $DB"
    if [ "$DB" = "gallery3" ]; then #gallery3 runs on MySQL
        mysqldump -u root $DB > $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql
    else
        pg_dump -U postgres $DB > $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql
    fi
    if [ -f $BACKUPHOME/$DB-latest.bz2 ]; then
	rm $BACKUPHOME/latest/$DB-latest.bz2
    fi
    echo "Compressing $DB-latest.bz2"
    pbzip2 -zc $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql >$BACKUPHOME/latest/$DB-latest.sql.bz2

    if [ -f $BACKUPPATH/$MONTHLYARCH/$DB-$MONTH-base.sql ]; then
	#If there is a base dump for the month, diff the current dump with the base and store that instead.
	diff $BACKUPPATH/$MONTHLYARCH/$DB-$MONTH-base.sql $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql  >$BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.diff

	rm $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql
    else
	mv $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql $BACKUPPATH/$MONTHLYARCH/$DB-$MONTH-base.sql
    fi
    echo "Compressing monthly archives of $DB"
    tar -c $MONTHLYARCH/ >$MONTHLYARCH.tar
    pbzip2 -f $MONTHLYARCH.tar
    rm -rf $BACKUPPATH/$MONTHLYARCH/
done

GLACIERARCH=glacier-$MMMYY
#GLACIERFILE=$BACKUPPATH/glacier/$GLACIERARCH
GLACIERFILE=/home/hkn/compserv/scripts/glacier/important_message.txt
IDSFILE=$BACKUPPATH/$GLACIERARCH-ids

#Compress all the dbs into one file
tar cvf $GLACIERFILE.tar .
pbzip2 -f $GLACIERFILE.tar

if [ ! -f $IDSFILE]; THEN
    touch $IDSFILE
fi

#Run Python script to upload to Glacier
source glacier/BOTO_ENV/bin/activate
#Save the archive ID to file
python glacier/upload.py $GLACIERFILE.tar.bz2 >> $IDSFILE
deactivate

rm -rf $BACKUPPATH/glacier/
