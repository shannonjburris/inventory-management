from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from flask import abort

from app.models.product import ProductCreate, ProductUpdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize(doc: dict) -> dict:
    """
    MongoDB documents use ObjectId for _id, which is not JSON-serializable.
    This converts ObjectId → plain string and renames _id → id so the API
    response looks clean. Think of it like a DTO (Data Transfer Object) mapper.
    """
    doc["id"] = str(doc.pop("_id"))
    return doc


def parse_object_id(id_str: str) -> ObjectId:
    """
    Validate and convert a string to a MongoDB ObjectId.
    Returns 400 immediately if the string is not a valid 24-character hex ID.
    """
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        abort(400, description="Invalid product ID format")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def get_all_products(db) -> list[dict]:
    """Return all products, newest first."""
    cursor = db.products.find().sort("created_at", -1)
    return [_serialize(doc) for doc in cursor]


def get_product_by_id(db, product_id: str) -> dict:
    """Return a single product or abort 404."""
    oid = parse_object_id(product_id)
    doc = db.products.find_one({"_id": oid})
    if doc is None:
        abort(404, description="Product not found")
    return _serialize(doc)


def create_product(db, payload: ProductCreate) -> dict:
    """Insert a new product and return it with its generated id."""
    now = _now()
    document = {
        **payload.model_dump(),   # unpack validated fields — like JS spread: { ...payload }
        "created_at": now,
        "updated_at": now,
    }
    result = db.products.insert_one(document)
    document["_id"] = result.inserted_id
    return _serialize(document)


def update_product(db, product_id: str, payload: ProductUpdate) -> dict:
    """
    Partially update a product. Only fields explicitly provided in the request
    body are updated — others are left unchanged.

    We build the $set document from only non-None fields. This means a client
    can send {"price": 49.99} and we won't accidentally null out product_name.
    """
    oid = parse_object_id(product_id)

    # Dictionary comprehension: keep only fields that were actually provided
    fields_to_update = {k: v for k, v in payload.model_dump().items() if v is not None}

    if not fields_to_update:
        abort(400, description="Request body must contain at least one field to update")

    fields_to_update["updated_at"] = _now()

    result = db.products.find_one_and_update(
        {"_id": oid},
        {"$set": fields_to_update},
        return_document=True,   # return the document AFTER the update
    )

    if result is None:
        abort(404, description="Product not found")

    return _serialize(result)


def delete_product(db, product_id: str) -> dict:
    """Delete a product and return the deleted document."""
    oid = parse_object_id(product_id)
    doc = db.products.find_one_and_delete({"_id": oid})
    if doc is None:
        abort(404, description="Product not found")
    return _serialize(doc)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

# The entire analytics computation runs inside MongoDB — no Python loops.
# $facet runs multiple sub-pipelines in a single pass over the collection.
# This is the MongoDB equivalent of a SQL query with multiple GROUP BY clauses.
# $round is used for clean decimal output. We do final rounding in Python rather
# than inside the pipeline so the pipeline stays compatible with mongomock in tests.
_ANALYTICS_PIPELINE = [
    {
        "$facet": {
            # Sub-pipeline A: one row of global totals
            "summary": [
                {
                    "$group": {
                        "_id": None,
                        "total_products": {"$sum": 1},
                        "overall_avg_price": {"$avg": "$price"},
                        "total_inventory_value": {
                            "$sum": {"$multiply": ["$price", "$available_quantity"]}
                        },
                    }
                }
            ],
            # Sub-pipeline B: one row per category, sorted by product count desc
            "by_category": [
                {
                    "$group": {
                        "_id": "$product_category",
                        "count": {"$sum": 1},
                        "avg_price": {"$avg": "$price"},
                        "total_quantity": {"$sum": "$available_quantity"},
                        "min_price": {"$min": "$price"},
                        "max_price": {"$max": "$price"},
                    }
                },
                {"$sort": {"count": -1}},
                {
                    "$project": {
                        "_id": 0,
                        "category": "$_id",
                        "product_count": "$count",
                        "avg_price": "$avg_price",
                        "total_quantity": 1,
                        "min_price": 1,
                        "max_price": 1,
                    }
                },
            ],
        }
    },
    # Flatten the $facet output — $facet wraps each sub-pipeline result in an array
    {
        "$project": {
            "total_products": {"$arrayElemAt": ["$summary.total_products", 0]},
            "overall_avg_price": {"$arrayElemAt": ["$summary.overall_avg_price", 0]},
            "total_inventory_value": {"$arrayElemAt": ["$summary.total_inventory_value", 0]},
            "most_popular_category": {
                # by_category is sorted desc by count, so index 0 is the top category
                "$arrayElemAt": ["$by_category.category", 0]
            },
            "by_category": 1,
        }
    },
]


def get_analytics(db) -> dict:
    """Run the aggregation pipeline and return the analytics summary."""
    results = list(db.products.aggregate(_ANALYTICS_PIPELINE))

    # $facet on an empty collection returns one document with empty arrays.
    # Normalize the result so all keys are always present with sensible defaults.
    if not results or not results[0].get("total_products"):
        return {
            "total_products": 0,
            "overall_avg_price": 0.0,
            "total_inventory_value": 0.0,
            "most_popular_category": None,
            "by_category": [],
        }

    data = results[0]
    # Ensure most_popular_category is always present (missing when by_category is empty)
    data.setdefault("most_popular_category", None)

    # Round floats to 2 decimal places for clean JSON output
    data["overall_avg_price"] = round(data.get("overall_avg_price") or 0, 2)
    data["total_inventory_value"] = round(data.get("total_inventory_value") or 0, 2)
    for cat in data.get("by_category", []):
        cat["avg_price"] = round(cat.get("avg_price") or 0, 2)

    return data
