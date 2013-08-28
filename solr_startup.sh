#!/bin/bash
su -s /bin/bash www-data;
cd /var/www/hkn-rails
echo $SHELL
#rake sunspot:solr:start RAILS_ENV=production >>/home/jkhoe/log 2>&1
rake sunspot:solr:reindex RAILS_ENV=production >>/home/jkhoe/log 2>&1
exit
apache2ctl restart >>/home/jkhoe/log 2>&1
exit;
