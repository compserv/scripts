#!/bin/bash

# Backup a dump of ldap; to be run nightly.

DATESTRING=`date +"%b%y"`
BACKUPHOME=/home/hkn/compserv/ldapbackups
BACKUPPATH=$BACKUPHOME/$DATESTRING.ldif
sudo slapcat > $BACKUPPATH