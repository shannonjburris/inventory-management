"""
conftest.py — shared pytest fixtures.

Fixtures defined here are automatically available to all test files.
Think of this like a Jest setup file, but scoped automatically by directory.
"""

import pytest
import mongomock

from app import create_app


@pytest.fixture()
def app():
    """
    Create a Flask app configured for testing.

    We monkeypatch `init_mongo` so MongoDB is replaced with an in-memory
    mongomock client — no real database needed for unit tests.
    """
    test_app = create_app("testing")

    # Replace the real MongoClient with an in-memory mock
    mock_client = mongomock.MongoClient()
    test_app.mongo_client = mock_client
    test_app.db = mock_client["inventory_test"]

    yield test_app   # `yield` is like returning, but cleanup code after it runs after each test


@pytest.fixture()
def client(app):
    """
    Flask test client — sends HTTP requests to the app without a real server.
    Equivalent to supertest in Node: `request(app).get('/products')`.
    """
    return app.test_client()


@pytest.fixture()
def sample_product(client):
    """
    Insert one product and return its JSON. Used as a shared setup across tests
    that need an existing product to GET, PUT, or DELETE.
    """
    response = client.post("/products", json={
        "product_name": "Test Feeder",
        "product_category": "Feeders",
        "price": 29.99,
        "available_quantity": 50,
    })
    return response.get_json()
