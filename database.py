import sqlite3
from flask import g


DATABASE = 'database.db'

def get_database():
    database = getattr(g, '_database', None)
    if database is None:
        database = g._database = sqlite3.connect(DATABASE)
        database.row_factory = sqlite3.Row
    return database

def close_database(exception=None):
    database = getattr(g, '_database', None)
    if database is not None:
        database.close()


def query_database(query, args=(), one=False, commit=False):
    if commit:
        print("commit")
        database = get_database()
        cur = database.execute(query, args)
        database.commit()
        cur.close
        return None
    cur = get_database().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def init_database(app):
    app.teardown_appcontext(close_database)