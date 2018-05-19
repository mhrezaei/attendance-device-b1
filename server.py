#!/usr/bin/env python
# from builtins import KeyboardInterrupt

from app.config import app, socket, publish, worker
from app.logic import receive, run_fingerprint, run_rfid

from threading import Thread, Event
import time
import os


def flask_handler():
    print(' 1 - SocketIO and Flask [ONLINE] ')
    worker.attach(receive)
    socket.run(app, host='0.0.0.0')
    # socket.run(app, log_output=True, debug=True) TODO: NOT working when debug mode is True


def fingerprint_handler(ev_fingerprint):
    print(' 2 - Fingerprint worker [ONLINE] ')
    while ev_fingerprint.is_set():
        run_fingerprint()


def rfid_handler(ev_rfid):
    print(' 3 - RFID worker        [ONLINE] ')
    while ev_rfid.is_set():
        run_rfid()


if __name__ == '__main__':
    event_fingerprint = Event()
    event_rfid = Event()
    try:
        event_fingerprint.set()
        event_rfid.set()
        fingerprint_thread = Thread(target=fingerprint_handler, args=(event_fingerprint,))
        rfid_thread = Thread(target=rfid_handler, args=(event_rfid,))
        flask_thread = Thread(target=flask_handler)
        flask_thread.start()
        time.sleep(0.1)
        fingerprint_thread.start()
        time.sleep(0.1)
        rfid_thread.start()
        time.sleep(0.1)
        while True: # This makes KeyboardInterrupt work and kill the running program
            time.sleep(0.01)
    except KeyboardInterrupt:
        print(' * Terminating... ')
        event_fingerprint.clear()
        event_rfid.clear()
        os.system('kill -9 %d' % os.getpid())
