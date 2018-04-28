from flask import Flask, send_file
from flask_socketio import SocketIO
from . import SocketWorker, Store
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

socket = SocketIO(app)
worker = SocketWorker()
publish = worker.publish
store = Store()

import routes


@socket.on('update')
def update():
    worker.update()


@app.route('/<path:path>')
def static_file(path):
    temp = os.path.dirname(os.path.realpath(__file__)) + '/public/' + path
    return send_file(temp)
