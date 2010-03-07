#!/bin/bash
MMMYY=`date +"%b%y"`
DATE=`date +"%Y-%m-%d"`
TIME=`date +"%H%M"`
BACKUPHOME=/home/hkn/compserv/dbbackups
BACKUPPATH=$BACKUPHOME/$MMMYY
DBLIST=(django_website_prod gallery2 indrel_database_production postgres redmine wikidb)
if [ ! -d $BACKUPPATH ]; then
    mkdir $BACKUPPATH
fi
cd $BACKUPPATH
for DB in "${DBLIST[@]}"; do
    MONTHLYARCH=$DB-$MMMYY
    if [ -f $MONTHLYARCH.tar.bz2 ]; then
	tar -xjf $MONTHLYARCH.tar.bz2
    else
	mkdir $MONTHLYARCH
    fi
    pg_dump -U postgres $DB > $BACKUPPATH/$MONTHLYARCH/$DB-$DATE.sql
    tar -cjf $MONTHLYARCH.tar.bz2 $MONTHLYARCH/
    
    if [ -f $BACKUPHOME/$DB-latest.bz2 ]; then
	rm $BACKUPHOME/$DB-latest.bz2
    fi
    bzip2 -zc $BACKUPPATH/$MONTHLYARCH/$DB-$DATE.sql >$BACKUPHOME/latest/$DB-latest.sql.bz2
    rm -rf $BACKUPPATH/$MONTHLYARCH/
done
