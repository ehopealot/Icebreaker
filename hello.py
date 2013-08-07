import os
import json

import re
from flask import Flask, request, Response
from bson import json_util
from urlparse import urlparse
from pymongo import Connection
from bson import ObjectId
from functools import wraps

def api(f):
    @wraps(f)
    def w(*args, **kwargs):
        return Response(json.dumps(f(*args, **kwargs), default=json_util.default), mimetype='text/json')
    return w

MONGO_URL = os.environ.get('MONGOHQ_URL')

if MONGO_URL:
    connection = Connection(MONGO_URL)
    db = connection[urlparse(MONGO_URL).path[1:]]
    debug = False
else:
    debug = True
    connection = Connection('localhost', 27017)
    db = connection['MyDB']

app = Flask(__name__)
app.debug = debug

@app.route('/')
@api
def hello():
    pageviews = db.test.find_one({'event':'page_views'})
    if not pageviews:
        pageviews = {'event':'page_views', 'count':1}
    else:
        pageviews['count'] += 1
    db.test.save(pageviews)
    return {'result':'Hello Worlddddddd!\nHack Week, Bitches!\n %i page views!' % pageviews['count']}


@app.route('/create_user/<email>')
@api
def create_user(email):
    email = re.search('[a-zA-Z0-9-_\+.]*@dropbox.com', email)
    if not email:
        return {'error': -1, 'message': 'must register with a dropbox email address'}

    email = email.group(0)
    user = db.user.find_one({'email': email})
    if user:
        return {'error': -2, 'message': 'user already exists'}
    else:
        user_id = db.user.insert({'email': email})
        return {'id': str(user_id)}

@app.route('/list_users')
@api
def list_users():
    users = db.user.find()
    toReturn = []
    for user in users:
        toReturn.append({'id': str(user['_id']), 'email': user['email']})
    return toReturn

@app.route('/users/<user_id>/facts', methods=['POST', 'GET'])
@api
def user_assignment(user_id):
    user = db.user.find_one(ObjectId(user_id))
    if request.method == 'POST':
        user['facts'].append(request.form['fact'])
        db.user.save(user)
        return {}
    else:
        return user['facts']
