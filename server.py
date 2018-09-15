#!/usr/bin/env python
# from builtins import KeyboardInterrupt

from app.config import app, socket, publish, worker
from app.logic import receive, run_fingerprint, run_rfid, run_led

from threading import Thread, Event
from time import strftime, localtime, time, sleep
import os


def flask_handler():
    """
    Run flask.

    """
    print(' 1 - SocketIO and Flask [ONLINE] ')
    worker.attach(receive)
    socket.run(app, host='0.0.0.0')


def fingerprint_handler(ev_fingerprint):
    """
    Run fingerprint if its event is set.

    :param ev_fingerprint: Event

    """
    print(' 2 - Fingerprint worker [ONLINE] ')
    while ev_fingerprint.is_set():
        run_fingerprint()


def rfid_handler(ev_rfid):
    """
    Run rfid if its event is set.

    :param ev_rfid: Event

    """
    print(' 3 - RFID worker        [ONLINE] ')
    while ev_rfid.is_set():
        run_rfid()


def led_handler(ev_led):
    """
    Run led if its event is set.

    :param ev_led: Event

    """
    print(' 4 - LED worker         [ONLINE] ')
    while ev_led.is_set():
        run_led()


if __name__ == '__main__':
    print('Start: ' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '\n\n')
    event_fingerprint = Event()
    event_rfid = Event()
    event_led = Event()

    try:
        event_fingerprint.set()
        event_rfid.set()
        event_led.set()
        fingerprint_thread = Thread(target=fingerprint_handler, args=(event_fingerprint,))
        rfid_thread = Thread(target=rfid_handler, args=(event_rfid,))
        flask_thread = Thread(target=flask_handler)
        led_thread = Thread(target=led_handler, args=(event_led,))
        flask_thread.start()
        sleep(0.1)
        fingerprint_thread.start()
        sleep(0.1)
        rfid_thread.start()
        sleep(0.1)
        led_thread.start()
        sleep(0.1)
        while True:  # This makes KeyboardInterrupt work and kill the running program
            sleep(0.01)

    except KeyboardInterrupt:
        print(' * Terminating... ')
        event_fingerprint.clear()
        event_rfid.clear()
        event_led.clear()
        os.system('kill -9 %d' % os.getpid())
