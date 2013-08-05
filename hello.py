import os
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
    return 'Hello Worlddddddd!\nHack Week, Bitches!\n %i page views!' % pageviews['count']
