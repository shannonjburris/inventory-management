# Inventory Management API

A RESTful inventory management system for bird-themed products, built with Python Flask and MongoDB. Includes full CRUD operations and a server-side analytics endpoint powered by MongoDB aggregation pipelines.

**Tech stack:** Python 3.12 · Flask 3.1 · MongoDB 7 · Pydantic v2 · Docker / Docker Compose

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Docker | 24.0 |
| Docker Compose | v2.20 |
| Python *(local dev only)* | 3.12 |

---

## Quick Start — Docker (recommended)

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd inventory-management

# 2. Build and start both services (Flask API + MongoDB)
docker-compose up --build -d

# 3. Seed the database with 15 sample bird products
docker exec inventory_api python scripts/seed.py

# 4. The API is now running at http://localhost:5000
curl http://localhost:5000/products
```

To stop: `docker-compose down`  
To stop and wipe all data: `docker-compose down -v`

---

## Quick Start — Local Development

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # optional: for running tests

# 3. Configure environment
cp .env.example .env              # edit MONGO_URI if your Mongo isn't on localhost

# 4. Seed the database (requires MongoDB running locally)
python scripts/seed.py

# 5. Start the development server
flask --app "app:create_app()" run --debug
```

The API runs at `http://localhost:5000`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Config profile: `development`, `production`, `testing` |
| `MONGO_URI` | `mongodb://localhost:27017/inventory_dev` | Full MongoDB connection URI including database name |

---

## API Reference

All responses use `Content-Type: application/json`.  
Error responses always follow this shape:
```json
{"error": {"code": 404, "message": "Product not found", "details": null}}
```

---

### List all products
```
GET /products
```
```bash
curl http://localhost:5000/products
```
**Response 200:**
```json
[
  {
    "id": "6630a1b2c3d4e5f6a7b8c9d0",
    "product_name": "Copper Tube Hummingbird Feeder",
    "product_category": "Feeders",
    "price": 34.99,
    "available_quantity": 75,
    "created_at": "2026-04-22T10:00:00Z",
    "updated_at": "2026-04-22T10:00:00Z"
  }
]
```

---

### Get a single product
```
GET /products/{id}
```
```bash
curl http://localhost:5000/products/6630a1b2c3d4e5f6a7b8c9d0
```
**Response 200:** single product object  
**Response 400:** invalid ID format  
**Response 404:** product not found

---

### Create a product
```
POST /products
Content-Type: application/json
```
```bash
curl -X POST http://localhost:5000/products \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Solar Bird Bath",
    "product_category": "Baths & Accessories",
    "price": 74.99,
    "available_quantity": 20
  }'
```
**Response 201:** created product with generated `id`  
**Response 400:** missing/invalid fields (all validation errors returned at once)

| Field | Type | Required | Constraints |
|---|---|---|---|
| `product_name` | string | yes | 1–200 chars |
| `product_category` | string | yes | 1–100 chars |
| `price` | number | yes | ≥ 0 |
| `available_quantity` | integer | yes | ≥ 0 |

---

### Update a product
```
PUT /products/{id}
Content-Type: application/json
```
All fields are optional — send only the ones you want to change.
```bash
curl -X PUT http://localhost:5000/products/6630a1b2c3d4e5f6a7b8c9d0 \
  -H "Content-Type: application/json" \
  -d '{"price": 29.99, "available_quantity": 100}'
```
**Response 200:** updated product  
**Response 400:** invalid fields or empty body  
**Response 404:** product not found

---

### Delete a product
```
DELETE /products/{id}
```
```bash
curl -X DELETE http://localhost:5000/products/6630a1b2c3d4e5f6a7b8c9d0
```
**Response 200:**
```json
{"message": "Product deleted", "product": { ... }}
```
**Response 404:** product not found

---

### Search products
```
GET /products?search=<query>
```
```bash
curl "http://localhost:5000/products?search=feeder"
```
Case-insensitive. Matches against both `product_name` and `product_category`.  
An empty or omitted `search` param returns the full product list.

**Response 200:** array of matching products (empty array if no matches)

---

### Health check
```
GET /health
```
```bash
curl http://localhost:5000/health
```
**Response 200** — API is up and MongoDB is reachable:
```json
{"status": "healthy", "database": "connected"}
```
**Response 503** — MongoDB is unreachable:
```json
{"status": "unhealthy", "database": "disconnected"}
```

---

### Analytics
```
GET /products/analytics
```
```bash
curl http://localhost:5000/products/analytics
```
**Response 200:**
```json
{
  "total_products": 15,
  "overall_avg_price": 62.38,
  "total_inventory_value": 28430.05,
  "most_popular_category": "Bird Food",
  "by_category": [
    {
      "category": "Bird Food",
      "product_count": 4,
      "avg_price": 14.12,
      "total_quantity": 850,
      "min_price": 9.99,
      "max_price": 18.99
    }
  ]
}
```

---

## Running Tests

```bash
# Activate venv first, then:
pytest tests/ -v
```

Tests use `mongomock` — an in-memory MongoDB mock — so no real database connection is needed.

---

## Project Structure

```
inventory-management/
├── app/
│   ├── __init__.py          # Application factory (create_app)
│   ├── config.py            # Dev / Prod / Test config classes
│   ├── extensions.py        # MongoDB connection management
│   ├── models/
│   │   └── product.py       # Pydantic schemas for request validation
│   ├── routes/
│   │   └── products.py      # All /products endpoints (Flask Blueprint)
│   ├── services/
│   │   └── product_service.py  # All database logic + analytics pipeline
│   └── errors/
│       └── handlers.py      # JSON error handlers (400, 404, 405, 500)
├── scripts/
│   └── seed.py              # Database seeder — 15 bird-themed products
├── tests/
│   ├── conftest.py          # Shared pytest fixtures (test client, mock DB)
│   ├── test_products.py     # CRUD endpoint tests
│   └── test_analytics.py    # Analytics endpoint tests
├── Dockerfile               # Multi-stage build, non-root user, gunicorn
├── docker-compose.yml       # Flask + MongoDB with health-check dependency
└── requirements.txt
```

---

## Troubleshooting

**API returns 503 on `/health`**  
MongoDB isn't reachable. Check the container is running and healthy:
```bash
docker-compose ps
docker-compose logs mongo
```

**`docker-compose up` starts the API but it crashes immediately**  
MongoDB likely didn't pass its healthcheck in time. Check its logs, then restart:
```bash
docker-compose logs mongo
docker-compose restart api
```

**Products list is empty after startup**  
The database needs to be seeded manually:
```bash
docker exec inventory_api python scripts/seed.py
```

**Port 5000 already in use**  
Another process is using the port. Find and stop it, or change the port mapping in `docker-compose.yml` from `"5000:5000"` to e.g. `"5001:5000"`.

**View live API logs**  
```bash
docker-compose logs -f api
```
All requests, errors, and create/update/delete operations are logged here.

---

## Design Decisions

**Push computation to MongoDB, not Python.**  
The analytics endpoint uses a single `$facet` aggregation pipeline that groups, sorts, and projects in one database round-trip. No Python loops or `sum()` calls touch the result set. This is the correct pattern for MongoDB — the database is optimized for this work; Python is not.

**Application factory pattern.**  
`create_app(env)` creates a fresh Flask instance instead of a module-level singleton. This lets us instantiate the app with different configs per test, and avoids circular imports between blueprints.

**Service layer.**  
All MongoDB calls live in `product_service.py`. Routes are thin — they parse input, call the service, return JSON. This separation makes the service mockable in tests and keeps route functions readable.

**gunicorn over Flask dev server.**  
Flask's built-in server is single-threaded and not production-safe. gunicorn spawns multiple worker processes and is the standard Python production WSGI server.

**MongoDB JSON Schema validator.**  
The schema constraint is applied at the collection level in `seed.py`, not just in application code. This means a direct `mongosh` insert must also satisfy the schema — the database is the final authority.

**Docker health-check dependency.**  
`depends_on: condition: service_healthy` waits for MongoDB's `ping` healthcheck to pass before starting the Flask container. This eliminates the startup race condition that would otherwise require a retry loop in the entrypoint script.
