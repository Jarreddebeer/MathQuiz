#!/usr/bin/env python
import psycopg2
import sys
import base64
import simplejson
import requests
from time import sleep
import statsd

from mathquiz import config

if not config.mixpanel_enabled:
    print 'analytics not enabled. Running this is pointless'
    sys.exit(0)

db = psycopg2.connect('user=%s password=%s' % (config.database_user, config.database_password))

c = db.cursor()
c.execute('listen analytics')
session = requests.Session()

try:
    while True:
        c.execute('SELECT data FROM analytics_queue')
        for row in c:
            print 'sending ', row
            result = session.get("http://api.mixpanel.com/track/?data=" + base64.b64encode(row[0]))
            print result

        c.execute('DELETE FROM analytics_queue')

        db.commit()
        if not db.notifies:
            print 'Notification list empty. Sleeping.'
        # while db has not notified yet
        while not db.notifies:
            sys.stdout.write('.')
            sys.stdout.flush()
            sleep(1)
            db.poll()

        db.notifies[:] = []
finally:
    c.close()
    db.close()
