import time
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
from random import choice, sample
from sets import Set

class api:
    def __init__(self, requires_user=False):
        self.requires_user = requires_user

    def __call__(self, f):
        @wraps(f)
        def w(*args, **kwargs):
            if self.requires_user:
                if not 'user_id' in kwargs:
                    return Response(status=404)
                possible_user_id = kwargs['user_id']
                user = db.user.find_one(ObjectId(possible_user_id))
                if user and 'authenticated' in user:
                    validate_schema(user)
                    args = (user,) + args
                    del kwargs['user_id']
                else:
                    return Response(status=401)
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

def validate_schema(user):
    if 'facts' not in user:
        user['facts'] = []
    if 'found_by' not in user:
        user['found_by'] = []
    if 'targets_found' not in user:
        user['targets_found'] = []
    if 'assignment' not in user:
        user['assignment'] = []
    if 'score' not in user:
        user['score'] = 0
    db.user.save(user)

def create_user_in_db(email, img):
    return db.user.insert({'email':email, 'facts':[], 'found_by':[],
                    'targets_found':[], 'assignment':[], 'score':0, 'image':img})

@app.route('/')
@api()
def hello():
    pageviews = db.test.find_one({'event':'page_views'})
    if not pageviews:
        pageviews = {'event':'page_views', 'count':1}
    else:
        pageviews['count'] += 1
    db.test.save(pageviews)
    return {'result':'Hello Worlddddddd!\nHack Week, Bitches!\n %i page views!' % pageviews['count']}

#utility route for us to populate the DB with dropboxers
@app.route('/create_user/<email>/<img>')
@api()
def create_user(email, img):
    email = re.search('[a-zA-Z0-9-_\+.]*@dropbox.com', email)
    if not email:
        return {'error': -1, 'message': 'must register with a dropbox email address'}

    email = email.group(0)
    user = db.user.find_one({'email': email})
    if user:
        return {'error': -2, 'message': 'user already exists'}
    else:
        full_url = "https://s3-us-west-2.amazonaws.com/guesswhoimages/" + img
        user_id = create_user_in_db(email, full_url)
        return {'id': str(user_id)}

#called when a user actually downloads the app and enters their email
@app.route('/register/<email>')
@api()
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

    message = PMMail(api_key = os.environ.get('POSTMARK_API_KEY'), subject = "Verify your email for Dropbox Guess Who!", sender = "andy+guesswho@dropbox.com", to = email, html_body = body)
    message.send()

    return {'success':'confirmation email sent to: %s' % email}

@app.route('/app_redirect/<user_id>')
def app_redirect(user_id):
    return redirect('GuessWho://%s' % user_id)

@app.route('/authenticate_user/<user_id>')
@api()
def authenticate_user(user_id):
    try:
        objectid = ObjectId(user_id)
        user = db.user.find_one({'_id': ObjectId(user_id)})
        if user:
            already = 0
            if 'authenticated' in user:
                already = 1
            else:
                user['authenticated'] = 1
                db.user.save(user)
            return {'success': 1, 'already_authenticated': already}
        else:
            return {'error': -1, 'message': 'invalid user id'}
    except:
        return {'error': -1, 'message': 'invalid user id'}

@app.route('/list_users')
@api()
def list_users():
    users = db.user.find()
    toReturn = []
    for user in users:
        try:
            toReturn.append({'id': str(user['_id']), 'email': user['email'], 'image': user['image']})
        except:
            pass
    return toReturn

@app.route('/users/<user_id>', methods=['GET'])
@api()
def user(user_id):
    user = db.user.find_one(ObjectId(user_id))
    return user

@app.route('/users/<user_id>/facts', methods=['POST'])
@api(requires_user=True)
def user_facts(user):
    user['facts'].append(request.form['fact'])
    db.user.save(user)
    return {}

def gen_assignment_info(user, target):
    halper_ids = sample(target['found_by'], min(len(target['found_by']), 4))
    halpers = []
    for halper_id in halper_ids:
        halper = db.user.find_one(ObjectId(halper_id))
        halpers.append({'email': halper['email']})
    fact = choice(target['facts']) if target['facts'] else "no fact"
    return {'target_id':str(target['_id']), 'fact':fact,
            'halpers':halpers}

def gen_new_assignment(user):
    users = db.user.find()
    valid_users = ['ehope@dropbox.com', 'mj@dropbox.com', 'andy@dropbox.com', 'chris.turney@dropbox.com', 'snark@dropbox.com']
    found_by = Set(user['found_by'])
    targets_found = Set(user['targets_found'])
    filter_set = found_by.union(targets_found).union(str(user['_id']))
    possible_targets = filter(lambda u: u['_id'] not in filter_set and u['email'] in valid_users, users)
    if not possible_targets:
        return {'error': -1, 'message': 'no more possible targets'}
    new_target = choice(possible_targets)
    #just for now
    validate_schema(new_target)
    user['assignment'] = [new_target['_id'], time.time()]
    db.user.save(user)
    return gen_assignment_info(user, new_target)

@app.route('/users/<user_id>/current_assignment')
@api(requires_user=True)
def current_assignment(user):
    if not user['assignment']:
        #if there's not assignment, make a new one
        return gen_new_assignment(user)
    target_id = user['assignment'][0]
    target = db.user.find_one(ObjectId(target_id))
    return gen_assignment_info(user, target)

@app.route('/users/<user_id>/skip_assignment')
@api(requires_user=True)
def skip_assignment(user):
    # blindly get a new assignment. This is called when an assignment is skipped
    return gen_new_assignment(user)

@app.route('/users/<user_id>/complete_assignment')
@api(requires_user=True)
def complete_assignment(user):
    assignment = user['assignment']
    if not assignment:
        return {'error': -1, 'message': 'there is no assignment for this user'}
    user['targets_found'].append(assignment[0])
    # do something about the score, also should probably validate
    # that this is a legit assignment completion somehow
    user['score'] += 1
    target = db.user.find_one(ObjectId(assignment[0]))
    target['found_by'].append(user['_id'])
    user['assignment'] = []
    db.user.save(user)
    db.user.save(target)
    return gen_new_assignment(user)

@app.route('/leaderboard')
@api()
def leaderboard():
    users = filter(lambda u: 'score' in u and u['score'], db.user.find())
    users = sorted(users, key=lambda u: -u['score'])
    leaderboard = [{'image':u['image'] if 'image' in u else "", 'name':u['email'], 'score':u['score']} for u in users]
    return leaderboard
