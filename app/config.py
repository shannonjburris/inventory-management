import os


class BaseConfig:
    """Settings shared across all environments."""
    JSON_SORT_KEYS = False          # preserve insertion order in JSON responses
    PROPAGATE_EXCEPTIONS = True     # let exceptions bubble up to our error handlers


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/inventory_dev")


class ProductionConfig(BaseConfig):
    DEBUG = False
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/inventory")


class TestingConfig(BaseConfig):
    TESTING = True
    MONGO_URI = os.getenv("MONGO_TEST_URI", "mongodb://localhost:27017/inventory_test")


# Maps the APP_ENV string to the right config class.
# In JS this would be: const CONFIG_MAP = { development: DevelopmentConfig, ... }
CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
