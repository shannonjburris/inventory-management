import logging
import os
from flask import Flask, jsonify, current_app
from dotenv import load_dotenv

from app.config import CONFIG_MAP
from app.extensions import init_mongo
from app.errors.handlers import register_error_handlers

# Module-level logger — each log line will be prefixed with this module's name
# making it easy to filter logs by source when debugging production issues
logger = logging.getLogger(__name__)


def create_app(env: str | None = None) -> Flask:
    """
    Application factory — creates and configures a Flask app instance.

    Why a factory instead of a module-level `app = Flask(__name__)`?
    A global app is created once when the file is imported and shared forever.
    Every test would share the same database and config, making them interfere
    with each other. The factory produces a fresh, isolated instance each call —
    one per test, one for production, one for development.
    """
    load_dotenv()  # read .env file into environment variables before anything else

    # Configure logging format once at startup.
    # In production this output is captured by gunicorn and visible via `docker-compose logs api`
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    app = Flask(__name__)

    # Use the passed-in env, or fall back to the APP_ENV environment variable.
    # This is how tests pass "testing" in directly without setting an env var.
    env = env or os.getenv("APP_ENV", "development")

    # CONFIG_MAP[env] picks the right config class (Dev/Prod/Test) by name
    # and loads all its settings onto the app at once
    app.config.from_object(CONFIG_MAP[env])

    # Connect to MongoDB and attach the db handle to the app.
    # Done before registering routes so the connection exists when requests arrive.
    init_mongo(app)

    # Register the products blueprint — all routes in products_bp get the
    # /products prefix automatically. Adding more resource types later
    # (e.g. /orders, /users) means just registering a new blueprint here.
    from app.routes.products import products_bp
    app.register_blueprint(products_bp, url_prefix="/products")

    # Registered last so these handlers catch errors from everywhere above —
    # routes, blueprints, and the database layer all funnel through here
    register_error_handlers(app)

    # Health check endpoint — intentionally outside the products blueprint.
    # Returns 200 if the API is up and MongoDB is reachable, 503 otherwise.
    # First thing to hit when investigating a production issue.
    @app.route("/health")
    def health_check():
        try:
            current_app.mongo_client.admin.command("ping")
            return jsonify({"status": "healthy", "database": "connected"}), 200
        except Exception as exc:
            logger.error("Health check failed: %s", exc)
            return jsonify({"status": "unhealthy", "database": "disconnected"}), 503

    logger.info("App started in '%s' environment", env)
    return app
