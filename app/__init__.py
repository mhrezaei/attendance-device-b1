from Queue import Queue


class Store:
    def __init__(self):
        self.data = dict()

    def has(self, key):
        if key in self.data:
            return True
        return False

    def remove(self, key):
        self.data.pop(key)

    def clear(self):
        self.data.clear()

    def get(self, key, default=None):
        if self.has(key):
            return self.data[key]
        else:
            return default

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, item):
        return self.data[item]


class SocketWorker(object):
    def __init__(self):
        self.subscriber = None
        self.actions = Queue()

    def detach(self):
        self.subscriber = None

    def attach(self, func):
        self.subscriber = func

    def publish(self, action, message):
        self.actions.put({'action': action, 'message': message})

    def update(self):
        while not self.actions.empty():
            ac = self.actions.get()
            if self.subscriber:
                self.subscriber(ac['action'], ac['message'])
                self.actions.task_done()
