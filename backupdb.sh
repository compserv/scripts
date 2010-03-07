#!/bin/bash
MMMYY=`date +"%b%y"`
DATE=`date +"%Y-%m-%d"`
TIME=`date +"%H%M"`
BACKUPHOME=/home/hkn/compserv/dbbackups
BACKUPPATH=/home/hkn/compserv/dbbackups/$MMMYY
DBLIST=(django_website_prod gallery2 indrel_database_production postgres redmine wikidb)
for DB in "${DBLIST[@]}"; do
    if [ ! -d $BACKUPPATH ]; then
	mkdir $BACKUPPATH
    fi
    pg_dump -U postgres $DB | bzip2 -zc > $BACKUPPATH/$DB-$DATE.bz2
 
    if [ -h $BACKUPHOME/$DB-latest.bz2 ]; then
	rm $BACKUPHOME/$DB-latest.bz2
    fi
    ln -s $BACKUPPATH/$DB-$DATE.bz2 $BACKUPHOME/latest/$DB-latest.bz2

done
