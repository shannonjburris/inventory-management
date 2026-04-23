"""Tests for CRUD endpoints: GET, POST, PUT, DELETE /products."""


class TestListProducts:
    def test_returns_empty_list_when_no_products(self, client):
        response = client.get("/products/")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_returns_all_products(self, client, sample_product):
        response = client.get("/products/")
        assert response.status_code == 200
        products = response.get_json()
        assert len(products) == 1
        assert products[0]["product_name"] == "Test Feeder"


class TestGetProduct:
    def test_returns_product_by_id(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.get(f"/products/{product_id}")
        assert response.status_code == 200
        assert response.get_json()["id"] == product_id

    def test_returns_404_for_unknown_id(self, client):
        response = client.get("/products/000000000000000000000000")
        assert response.status_code == 404

    def test_returns_400_for_invalid_id_format(self, client):
        response = client.get("/products/not-a-valid-id")
        assert response.status_code == 400


class TestCreateProduct:
    def test_creates_product_successfully(self, client):
        response = client.post("/products", json={
            "product_name": "Bluebird House",
            "product_category": "Birdhouses",
            "price": 44.99,
            "available_quantity": 20,
        })
        assert response.status_code == 201
        body = response.get_json()
        assert body["product_name"] == "Bluebird House"
        assert "id" in body

    def test_returns_400_for_missing_fields(self, client):
        response = client.post("/products", json={"product_name": "Incomplete"})
        assert response.status_code == 400

    def test_returns_400_for_negative_price(self, client):
        response = client.post("/products", json={
            "product_name": "Bad Product",
            "product_category": "Feeders",
            "price": -5.0,
            "available_quantity": 10,
        })
        assert response.status_code == 400

    def test_returns_400_for_non_json_body(self, client):
        response = client.post("/products", data="not json", content_type="text/plain")
        assert response.status_code == 400


class TestUpdateProduct:
    def test_updates_single_field(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.put(f"/products/{product_id}", json={"price": 39.99})
        assert response.status_code == 200
        assert response.get_json()["price"] == 39.99
        # Other fields should be unchanged
        assert response.get_json()["product_name"] == "Test Feeder"

    def test_returns_404_for_unknown_product(self, client):
        response = client.put("/products/000000000000000000000000", json={"price": 10.0})
        assert response.status_code == 404

    def test_returns_400_for_empty_update_body(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.put(f"/products/{product_id}", json={})
        assert response.status_code == 400


class TestDeleteProduct:
    def test_deletes_product_successfully(self, client, sample_product):
        product_id = sample_product["id"]
        response = client.delete(f"/products/{product_id}")
        assert response.status_code == 200

        # Confirm it's gone
        get_response = client.get(f"/products/{product_id}")
        assert get_response.status_code == 404

    def test_returns_404_for_unknown_product(self, client):
        response = client.delete("/products/000000000000000000000000")
        assert response.status_code == 404
