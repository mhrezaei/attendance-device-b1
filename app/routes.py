from config import app, publish, store, socket
from flask import render_template, request, flash, redirect, url_for

store['clients'] = []


# --------------#
#   Sockets     #
#               #
# --------------#
@socket.on('connect')
def socket_connect():
    socket.emit('auth', request.sid)
    store['clients'].append(request.sid)


@socket.on('disconnect')
def socket_disconnect():
    store['clients'].remove(request.sid)


@socket.on('setFingerPrintStatus')
def set_fingerprint_status(data):
    store['fingerPrintEnabled'] = data


@app.before_request
def before_any_request():
    store['fingerPrintEnabled'] = False

# --------------#
#   Endpoints   #
#               #
# --------------#
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/settings') #TODO: If no action is done on this page for about one minute, leads to Broken Pipe Eroor on terminal but yet everything works fine
def settings():
    return render_template('settings.html')

