import os
import json

import re
from flask import Flask, request, Response, redirect
from bson import json_util
from urlparse import urlparse
from pymongo import Connection
from bson import ObjectId
from functools import wraps
from postmark import PMMail

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

#utility route for us to populate the DB with dropboxers
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

#called when a user actually downloads the app and enters their email
@app.route('/register/<email>')
@api
def register(email):
    user = db.user.find_one({'email': email})
    # check if the user is present in the database.  If not then they aren't a real dropboxer
    if not user:
        return {'error': -1, 'message':'You are not a real Dropboxer.'}

    # check if the user is authenticated already
    if 'authenticated' in user:
        return {'error': -2, 'message':'This email address is already registered.'}

    body = """
    <html>
    <body>
    <center>
    <h2>Welcome to Dropbox Guess Who!</h2>
    <br/>
    Click the link below (on your mobile device) to start playing Guess Who.
    <br/>
    <h1><a href="http://limitless-caverns-4433.herokuapp.com/app_redirect/%s">Click Here!</a></h1>
    <br/>
    If you don't know why you received this email...
    </center>
    </body>
    </html>
    """ % str(user['_id'])

    message = PMMail(api_key = "ce8cb599-bbc6-4c49-88ee-838268ebcb40", subject = "Verify your email for Dropbox Guess Who!", sender = "andy+guesswho@dropbox.com", to = email, html_body = body)
    message.send()
    
    return {'success':'confirmation email sent to: %s' % email}

@app.route('/app_redirect/<user_id>')
def app_redirect(user_id):
    return redirect('GuessWho://%s' % user_id)

@app.route('/authenticate_user/<email>/<user_id>')
@api
def authenticate_user(email, user_id):
    try:
        objectid = ObjectId(user_id)
        user = db.user.find_one({'email': email, '_id': ObjectId(user_id)})
        if user:
            already = 0 
            if 'authenticated' in user:
                already = 1

            user['authenticated'] = 1
            db.user.save(user)
            return {'success': 1, 'already_authenticated': already}
        else:
            return {'error': -1, 'message': "user id and email don't match"}
    except:
        return {'error': -2, 'message': 'invalid user id'}

@app.route('/list_users')
@api
def list_users():
    users = db.user.find()
    toReturn = []
    for user in users:
        toReturn.append({'id': str(user['_id']), 'email': user['email']})
    return toReturn

@app.route('/users/<user_id>', methods=['GET'])
@api
def user_assignment(user_id):
    user = db.user.find_one(ObjectId(user_id))
    if request.method == 'POST':
        user['facts'].append(request.form['fact'])
        db.user.save(user)
        return {}
    else:
        return user

@app.route('/users/<user_id>/facts', methods=['POST'])
@api
def user_facts(user_id):
    user = db.user.find_one(ObjectId(user_id))
    user['facts'].append(request.form['fact'])
    db.user.save(user)
    return {}
