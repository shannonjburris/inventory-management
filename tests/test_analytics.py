"""Tests for GET /products/analytics."""


class TestAnalytics:
    def test_returns_zeros_when_no_products(self, client):
        response = client.get("/products/analytics")
        assert response.status_code == 200
        body = response.get_json()
        assert body["total_products"] == 0
        assert body["overall_avg_price"] == 0.0
        assert body["most_popular_category"] is None
        assert body["by_category"] == []

    def test_counts_total_products(self, client):
        # Insert 3 products
        for i in range(3):
            client.post("/products", json={
                "product_name": f"Product {i}",
                "product_category": "Feeders",
                "price": 10.0,
                "available_quantity": 5,
            })

        response = client.get("/products/analytics")
        assert response.get_json()["total_products"] == 3

    def test_identifies_most_popular_category(self, client):
        # 2 Feeders, 1 Birdhouses
        for _ in range(2):
            client.post("/products", json={
                "product_name": "A Feeder",
                "product_category": "Feeders",
                "price": 20.0,
                "available_quantity": 10,
            })
        client.post("/products", json={
            "product_name": "A House",
            "product_category": "Birdhouses",
            "price": 50.0,
            "available_quantity": 5,
        })

        response = client.get("/products/analytics")
        assert response.get_json()["most_popular_category"] == "Feeders"

    def test_calculates_average_price(self, client):
        client.post("/products", json={
            "product_name": "Cheap Seed",
            "product_category": "Bird Food",
            "price": 10.0,
            "available_quantity": 100,
        })
        client.post("/products", json={
            "product_name": "Fancy Binoculars",
            "product_category": "Optics & Gear",
            "price": 30.0,
            "available_quantity": 10,
        })

        response = client.get("/products/analytics")
        assert response.get_json()["overall_avg_price"] == 20.0

    def test_analytics_route_not_confused_with_id_route(self, client):
        # Ensures GET /products/analytics is not treated as GET /products/<id>
        response = client.get("/products/analytics")
        assert response.status_code == 200   # not 400 "Invalid product ID format"
