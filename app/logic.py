from time import sleep, time
from config import store, socket, publish


def receive(action, message):
    if action == 'message':
        print(message)
        socket.emit('message', str(message), broadcast=True)
        sleep(0.2)
    pass


def run():
    store['counter'] = store.get('counter', 0) + 1
    sleep(1.0)
