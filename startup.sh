#!/bin/sh

# inspircd
su irc -c 'cd /hkn/compserv/irc/inspircd/run; ./inspircd start'

# qwebirc
cd /var/www/qwebirc
python run.py -C /etc/ssl/hkn.eecs.berkeley.edu.crt -k /etc/ssl/hkn.eecs.berkeley.edu.key

# atheme-services
/hkn/compserv/irc/atheme/bin/bin/atheme-services

# solr
su -s /bin/bash -c 'cd /var/www/hkn-rails; bundle exec rake sunspot:solr:start RAILS_ENV=production; bundle exec rake sunspot:solr:reindex RAILS_ENV=production' - www-data
apache2ctl restart

# pytail
screen -dmS pytail python /home/gafyd/pygafyd/pytail.py
