#!/bin/bash

# Using mailman's list_lists script, this will generate all the necessary
# entries for the @@mailman file

# $ ./mailman_aliases.sh ~hkn/compserv/mmlist/maillists/@@mailman

echo > $1
mm="|/var/lib/mailman/mail/mailman"
for list in `/usr/lib/mailman/bin/list_lists -b`; do 
    echo -e "$list:\t\"$mm post $list\"" >> $1
    for action in admin bounces confirm join leave owner request subscribe unsubscribe; do
        echo -e "$list-$action:\t\"$mm $action $list\"" >> $1
    done
    echo >> $1
done
