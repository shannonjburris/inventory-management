import os


class BaseConfig:
    """Settings shared across all environments."""
    JSON_SORT_KEYS = False      # preserve insertion order in JSON responses
    PROPAGATE_EXCEPTIONS = True # let unhandled exceptions reach our error handlers
                                # rather than being swallowed silently by Flask
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # reject request bodies larger than 1 MB


# Each environment is its own class rather than a single class with if/else blocks.
# This makes it impossible to accidentally mix settings — dev debug mode can never
# leak into production.

class DevelopmentConfig(BaseConfig):
    DEBUG = True   # enables the interactive debugger and auto-reloader
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/inventory_dev")


class ProductionConfig(BaseConfig):
    DEBUG = False  # never expose stack traces or the debugger in production
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/inventory")


class TestingConfig(BaseConfig):
    TESTING = True
    # Separate URI so tests always hit an isolated database and never touch real data
    MONGO_URI = os.getenv("MONGO_TEST_URI", "mongodb://localhost:27017/inventory_test")


# Maps the APP_ENV string to the right config class.
# create_app() does CONFIG_MAP[env] to get the right class without a chain of if/else.
CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
