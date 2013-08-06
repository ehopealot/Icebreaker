import os
import json

import re
from flask import Flask, request, Response
from bson import json_util
from urlparse import urlparse
from pymongo import Connection
from bson import ObjectId


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
def hello():
    pageviews = db.test.find_one({'event':'page_views'})
    if not pageviews:
        pageviews = {'event':'page_views', 'count':1}
    else:
        pageviews['count'] += 1
    db.test.save(pageviews)
    toReturn = {'result':'Hello Worlddddddd!\nHack Week, Bitches!\n %i page views!' % pageviews['count']}
    return Response(json.dumps(toReturn), mimetype='text/json')

@app.route('/create_user/<email>')
def create_user(email):
    email = re.search('[a-zA-Z0-9-_\+.]*@dropbox.com', email)
    if not email:
        return Response(json.dumps({'error': -1, 'message': 'must register with a dropbox email address'}), mimetype='text/json')

    email = email.group(0)
    user = db.user.find_one({'email': email})
    if user:
        return Response(json.dumps({'error': -2, 'message': 'user already exists'}), mimetype='text/json')

    else:
        user_id = db.user.insert({'email': email})
        return Response(json.dumps({'id': str(user_id)}), mimetype='text/json')

@app.route('/list_users')
def list_users():
    users = db.user.find()
    toReturn = []
    for user in users:
        toReturn.append({'id': str(user['_id']), 'email': user['email']})
    return Response(json.dumps(toReturn), mimetype='text/json')

@app.route('/users/<user_id>/facts', methods=['POST', 'GET'])
def user_assignment(user_id):
    user = db.user.find_one(ObjectId(user_id))
    if request.method == 'POST':
        user['facts'].append(request.form['fact'])
        db.user.save(user)
        return Response(json.dumps({}), mimetype='text/json')
    else:
        return Response(json.dumps(user['facts']), mimetype='text/json')
