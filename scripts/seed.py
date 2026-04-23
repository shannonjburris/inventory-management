"""
Seed script — populates the inventory database with sample bird-themed products.

Run locally:   python scripts/seed.py
Run in Docker: docker exec inventory_api python scripts/seed.py

The script is idempotent: it drops the existing collection before inserting,
so re-running it always produces a clean, consistent dataset.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow importing from the project root when run as a standalone script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, TEXT

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/inventory")
DB_NAME = MONGO_URI.rstrip("/").split("/")[-1]

# ---------------------------------------------------------------------------
# MongoDB collection-level JSON Schema validator.
# This enforces the schema at the DATABASE layer — even direct mongosh inserts
# must pass validation. Think of it as a DB migration / constraint in SQL.
# ---------------------------------------------------------------------------
PRODUCT_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["product_name", "product_category", "price", "available_quantity"],
        "additionalProperties": True,
        "properties": {
            "product_name": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 200,
            },
            "product_category": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 100,
            },
            "price": {
                "bsonType": "double",
                "minimum": 0,
            },
            "available_quantity": {
                "bsonType": "int",
                "minimum": 0,
            },
        },
    }
}

# ---------------------------------------------------------------------------
# Sample products — 15 bird-themed items across 5 categories
# ---------------------------------------------------------------------------
now = datetime.now(timezone.utc)

SAMPLE_PRODUCTS = [
    # Bird Food (4)
    {
        "product_name": "Premium Sunflower Seed Mix",
        "product_category": "Bird Food",
        "price": 18.99,
        "available_quantity": 200,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Nyjer Thistle Seed (5 lb)",
        "product_category": "Bird Food",
        "price": 14.99,
        "available_quantity": 150,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Hummingbird Nectar Concentrate",
        "product_category": "Bird Food",
        "price": 9.99,
        "available_quantity": 320,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Mealworm Treat Blend (16 oz)",
        "product_category": "Bird Food",
        "price": 12.49,
        "available_quantity": 180,
        "created_at": now,
        "updated_at": now,
    },
    # Feeders (4)
    {
        "product_name": "Copper Tube Hummingbird Feeder",
        "product_category": "Feeders",
        "price": 34.99,
        "available_quantity": 75,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Squirrel-Proof Tube Feeder (6-Port)",
        "product_category": "Feeders",
        "price": 49.99,
        "available_quantity": 45,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Suet Cage Feeder (Double)",
        "product_category": "Feeders",
        "price": 19.99,
        "available_quantity": 100,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Platform Tray Feeder with Roof",
        "product_category": "Feeders",
        "price": 27.99,
        "available_quantity": 60,
        "created_at": now,
        "updated_at": now,
    },
    # Birdhouses (3)
    {
        "product_name": "Bluebird Nesting Box (Cedar)",
        "product_category": "Birdhouses",
        "price": 44.99,
        "available_quantity": 30,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Screech Owl House (Weathered Pine)",
        "product_category": "Birdhouses",
        "price": 59.99,
        "available_quantity": 15,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Purple Martin Colony House (12-Room)",
        "product_category": "Birdhouses",
        "price": 89.99,
        "available_quantity": 10,
        "created_at": now,
        "updated_at": now,
    },
    # Optics & Gear (3)
    {
        "product_name": "8x42 Waterproof Birding Binoculars",
        "product_category": "Optics & Gear",
        "price": 199.99,
        "available_quantity": 25,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Field Guide: Birds of North America",
        "product_category": "Optics & Gear",
        "price": 29.99,
        "available_quantity": 120,
        "created_at": now,
        "updated_at": now,
    },
    {
        "product_name": "Binocular Neck Strap (Neoprene)",
        "product_category": "Optics & Gear",
        "price": 16.99,
        "available_quantity": 90,
        "created_at": now,
        "updated_at": now,
    },
    # Baths & Accessories (1)
    {
        "product_name": "Solar-Powered Bubbling Bird Bath",
        "product_category": "Baths & Accessories",
        "price": 74.99,
        "available_quantity": 20,
        "created_at": now,
        "updated_at": now,
    },
]


def seed():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    print(f"Connected to MongoDB: {MONGO_URI}")
    print(f"Database: {DB_NAME}")

    # 1. Drop the collection so re-runs are idempotent
    db.products.drop()
    print("Dropped existing 'products' collection")

    # 2. Re-create the collection with the JSON Schema validator
    db.create_collection("products", validator=PRODUCT_VALIDATOR, validationLevel="strict")
    print("Created 'products' collection with schema validator")

    # 3. Create indexes for efficient querying and analytics
    db.products.create_index([("product_category", ASCENDING)], name="category_idx")
    db.products.create_index([("price", ASCENDING)], name="price_idx")
    db.products.create_index([("product_name", TEXT)], name="name_text_idx")
    print("Created indexes: category_idx, price_idx, name_text_idx")

    # 4. Insert sample products
    result = db.products.insert_many(SAMPLE_PRODUCTS)
    print(f"Inserted {len(result.inserted_ids)} bird-themed products across 5 categories")
    print("Seed complete!")

    client.close()


if __name__ == "__main__":
    seed()
