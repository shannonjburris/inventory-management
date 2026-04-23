from pymongo import MongoClient
from flask import current_app


def init_mongo(app):
    """
    Connect a MongoClient and store the database on the app object.
    Called once at startup from the application factory.
    """
    uri = app.config["MONGO_URI"]
    db_name = uri.rstrip("/").split("/")[-1]
    app.mongo_client = MongoClient(uri)
    app.db = app.mongo_client[db_name]


def get_db():
    """
    Return the database for the current Flask app.
    `current_app` is Flask's proxy — inside a request it points to the active app.
    Think of it like accessing a global singleton scoped to the running app instance.
    """
    return current_app.db
