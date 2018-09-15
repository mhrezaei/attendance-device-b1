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
    """
    User model, associated with the 'users' table.
    """
    __table__ = 'users'
    __guarded__ = ['id']


class Finger(Model):
    """
    Finger model, associated with the 'fingers' table.
    """
    __table__ = 'fingers'
    __guarded__ = ['id']


class UserLog(Model):
    """
    UserLog model, associated with the 'user_logs' table.
    """
    __table__ = 'user_logs'
    __guarded__ = ['id']
    __fillable__ = ['is_synced']
