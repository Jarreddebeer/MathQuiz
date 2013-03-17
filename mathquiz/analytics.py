from pyga import FlaskGATracker
from flask import request, session

import subprocess
import base64
import simplejson
from time import time

from mathquiz import app, config, database

@app.before_request
def google_track():
    if config.analytics_enabled:
        tracker = FlaskGATracker(config.analytics_account, config.analytics_domain)
        tracker.track(request, session, str(session['userId']))

if config.mixpanel_enabled:
    def track(event, properties=None):
        if properties == None:
            properties = {}

        token = config.mixpanel_token
        properties['distinct_id'] = session['userId']
        properties['mp_name_tag'] = session['username']
        properties['time'] = int(time())
        if 'X-Forwarded-For' in request.headers:
            properties['ip'] = request.headers['']

        if "token" not in properties:
            properties["token"] = token

        database.add_analytics(event, properties)

else:
    def track(*args):
        print 'not tracking. mixpanel disabled', args
        pass
