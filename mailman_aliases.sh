#!/bin/bash

# Using mailman's list_lists script, this will generate all the necessary
# entries for the @@mailman file

# $ ./mailman_aliases.sh > ~hkn/compserv/mmlist/maillists/@@mailman

mm="|/var/lib/mailman/mail/mailman"
for list in `/usr/lib/mailman/bin/list_lists -b`; do 
    echo -e "$list:\t\"$mm post $list\""
    for action in admin bounces confirm join leave owner request subscribe unsubscribe; do
        echo -e "$list-$action:\t\"$mm $action $list\""
    done
    echo
done
