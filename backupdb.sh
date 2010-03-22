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
DBLIST=(django_website_prod gallery2 indrel_database_production postgres redmine wikidb)
if [ ! -d $BACKUPPATH ]; then
    mkdir $BACKUPPATH
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
    pg_dump -U postgres $DB > $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql
    pbzip2 -zc $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql >$BACKUPHOME/latest/$DB-latest.sql.bz2
    if [ -f $BACKUPHOME/$DB-latest.bz2 ]; then
	rm $BACKUPHOME/$DB-latest.bz2
    fi
    if [ -f $BACKUPPATH/$MONTHLYARCH/$DB-$MONTH-base.sql ]; then
	#If there is a base dump for the month, diff the current dump with the base and store that instead.
	diff $BACKUPPATH/$MONTHLYARCH/$DB-$MONTH-base.sql $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql  >$BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.diff

	rm $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql
    else
	mv $BACKUPPATH/$MONTHLYARCH/$DB-$DATE-$TIME.sql $BACKUPPATH/$MONTHLYARCH/$DB-$MONTH-base.sql
    fi
    tar -cjf $MONTHLYARCH.tar.bz2 $MONTHLYARCH/
    rm -rf $BACKUPPATH/$MONTHLYARCH/
done
