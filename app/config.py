from flask import Flask, send_file
from flask_socketio import SocketIO
from . import SocketWorker, Store
import os

from pyfingerprint.pyfingerprint import PyFingerprint

fingerPrint = PyFingerprint('/dev/ttyUSB0', 57600, 0xFFFFFFFF, 0x00000000)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

socket = SocketIO(app)
worker = SocketWorker()
publish = worker.publish
store = Store()

import routes

import routes
from models import *


@socket.on('update')
def update():
    worker.update()


@app.route('/<path:path>')
def static_file(path):
    temp = os.path.dirname(os.path.realpath(__file__)) + '/public/' + path
    return send_file(temp)
