import os
import json
import re
from flask import Flask
from urlparse import urlparse
from pymongo import Connection

MONGO_URL = os.environ.get('MONGOHQ_URL')

if MONGO_URL:
    connection = Connection(MONGO_URL)
    db = connection[urlparse(MONGO_URL).path[1:]]
else:
    connection = Connection('localhost', 27017)
    db = connection['MyDB']

app = Flask(__name__)

@app.route('/')
def hello():
    pageviews = db.test.find_one({'event':'page_views'})
    if not pageviews:
        pageviews = {'event':'page_views', 'count':1}
    else:
        pageviews['count'] += 1
    db.test.save(pageviews)
    toReturn = {'result':'Hello Worlddddddd!\nHack Week, Bitches!\n %i page views!' % pageviews['count']}
    return json.dumps(toReturn)

@app.route('/create_user/<email>')
def create_user(email):
    email = re.search('[a-zA-Z0-9-_\+.]*@dropbox.com', email)
    if not email:
        return json.dumps({'error': -1, 'message': 'must register with a dropbox email address'})
    email = email.group(0)
    user = db.user.find_one({'email': email})
    if user:
        return json.dumps({'error': -2, 'message': 'user already exists'})
    else:
        user_id = db.user.insert({'email': email})
        return json.dumps({'id': str(user_id)})

@app.route('/list_users')
def list_users():
    users = db.user.find()
    toReturn = []
    for user in users:
        toReturn.append({'id': str(user['_id']), 'email': user['email']})
    return json.dumps(toReturn)
