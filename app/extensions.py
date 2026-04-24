from pymongo import MongoClient
from flask import current_app


def init_mongo(app):
    """
    Open a MongoDB connection and attach it to the app instance.
    Called once at startup from the application factory (app/__init__.py).

    Why attach to the app instead of storing in a module-level global?
    A global connection would be shared across every app instance — including
    test instances that are supposed to use a separate in-memory database.
    Attaching to `app` means each instance carries its own connection,
    so swapping in a mock database in tests doesn't affect anything else.
    """
    uri = app.config["MONGO_URI"]

    # The database name is the last segment of the URI after the final slash.
    # e.g. "mongodb://localhost:27017/inventory" → "inventory"
    db_name = uri.rstrip("/").split("/")[-1]

    app.mongo_client = MongoClient(uri)
    app.db = app.mongo_client[db_name]  # app.db is what routes actually query


def get_db():
    """
    Return the database handle for whichever app is currently handling this request.

    Why not just use `app.db` directly?
    Outside of a request, `app` doesn't exist as a variable — Flask uses
    `current_app` as a proxy that automatically points to the right app instance
    during a request. This lets the service layer call get_db() without needing
    to import or pass the app object around explicitly.
    """
    return current_app.db
