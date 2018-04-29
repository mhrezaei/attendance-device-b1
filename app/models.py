
from orator import DatabaseManager, Model


# Connect to our MySQL database
config = {
    'mysql': {
        'driver': 'mysql',
        'host': 'localhost',
        'database': 'attendance',
        'user': 'jafar',
        'password': '12345678',
        'prefix': ''
    }
}

db = DatabaseManager(config)
Model.set_connection_resolver(db)


class User(Model):
    __table__ = 'users'


class Finger(Model):
    __table__ = 'fingers'


class UserLog(Model):
    __table__ = 'user_logs'
