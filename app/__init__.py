import os
from flask import Flask
from dotenv import load_dotenv

from app.config import CONFIG_MAP
from app.extensions import init_mongo
from app.errors.handlers import register_error_handlers


def create_app(env: str | None = None) -> Flask:
    """
    Application factory — creates and configures a Flask app instance.

    Why a factory instead of a module-level `app = Flask(...)`?
    - Lets us create multiple app instances (e.g. one per test) with different configs
    - Prevents circular imports — blueprints are registered here, not at import time
    - Makes the app testable without spinning up a real server

    In Express terms: this is like `module.exports = (config) => { const app = express(); return app; }`
    """
    load_dotenv()   # reads .env file into os.environ — like dotenv in Node

    app = Flask(__name__)

    # Select config class based on APP_ENV env var (default: development)
    env = env or os.getenv("APP_ENV", "development")
    app.config.from_object(CONFIG_MAP[env])

    # Initialize MongoDB connection and attach db to app
    init_mongo(app)

    # Register the products blueprint under /products
    # This is like: app.use('/products', productsRouter) in Express
    from app.routes.products import products_bp
    app.register_blueprint(products_bp, url_prefix="/products")

    # Register JSON error handlers for 400, 404, 405, 500
    register_error_handlers(app)

    return app
