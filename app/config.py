from flask import Flask, send_file
from flask_socketio import SocketIO
from . import SocketWorker, Store
import os

from pyfingerprint.pyfingerprint import PyFingerprint

fingerprint = PyFingerprint('/dev/ttyUSB0', 57600, 0xFFFFFFFF, 0x00000000)

app = Flask(__name__)
app.config['SECRET_KEY'] = r'\x14Y\x1c\xd7\x105\xf1\xb5\xee\xb6\x03\x92\xae\x1e\xe1\xce\x14p\xd1\x13\r?\x88f\x10+\xff\xee|!'

socket = SocketIO(app)
worker = SocketWorker()
publish = worker.publish
store = Store()

api_token = '760483978406f1195959ef81a90c91ef'


import routes

import routes
from models import *

import routes


@socket.on('update')
def update():
    worker.update()


@app.route('/<path:path>')
def static_file(path):
    temp = os.path.dirname(os.path.realpath(__file__)) + '/public/' + path
    return send_file(temp)
