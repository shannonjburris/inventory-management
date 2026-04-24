import logging
import re
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from flask import abort

from app.models.product import ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize(doc: dict) -> dict:
    """
    Convert a raw MongoDB document into a clean JSON-safe dictionary.

    Why is this needed? MongoDB stores a special type called ObjectId for _id.
    ObjectId is not JSON-serializable — Flask would crash trying to convert it.
    This function converts ObjectId → plain string and renames _id → id.
    Every function that returns data to the route layer calls this.
    """
    doc["id"] = str(doc.pop("_id"))
    return doc


def parse_object_id(id_str: str) -> ObjectId:
    """
    Convert the ID string from the URL into a MongoDB ObjectId.

    MongoDB IDs must be exactly 24 hex characters. If a client sends
    /products/not-a-valid-id, MongoDB would raise a low-level error.
    Catching it here returns a clean 400 with a clear message instead.
    """
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        logger.warning("Invalid product ID format received: %s", id_str)
        abort(400, description="Invalid product ID format")


def _now() -> datetime:
    # Always UTC so timestamps are consistent regardless of server timezone
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def get_all_products(db) -> list[dict]:
    """Return all products, newest first."""
    cursor = db.products.find().sort("created_at", -1)
    return [_serialize(doc) for doc in cursor]


def search_products(db, query: str) -> list[dict]:
    """
    Case-insensitive search across product_name and product_category.

    $regex matches documents where the field contains the search term anywhere.
    $options "i" makes it case-insensitive — "feeder" matches "Feeder".
    re.escape() prevents special characters like . or * in the query from being
    treated as regex operators — protects against injection attacks.
    $or means either field can match — searching "feeders" returns products
    in the Feeders category even if the name doesn't contain that word.
    """
    pattern = {"$regex": re.escape(query), "$options": "i"}
    cursor = db.products.find(
        {"$or": [{"product_name": pattern}, {"product_category": pattern}]}
    ).sort("created_at", -1)
    return [_serialize(doc) for doc in cursor]


def get_product_by_id(db, product_id: str) -> dict:
    """Return a single product or abort 404."""
    oid = parse_object_id(product_id)
    doc = db.products.find_one({"_id": oid})
    if doc is None:
        abort(404, description="Product not found")
    return _serialize(doc)


def create_product(db, payload: ProductCreate) -> dict:
    """Insert a new product and return the created document."""
    now = _now()
    document = {
        **payload.model_dump(),  # spread all validated fields into the document
        "created_at": now,       # timestamps added here, not trusted from the client
        "updated_at": now,
    }
    result = db.products.insert_one(document)
    # insert_one returns metadata, not the document itself — we attach the
    # generated ID back onto our dict so _serialize can convert it to a string
    document["_id"] = result.inserted_id
    logger.info("Product created: id=%s", result.inserted_id)
    return _serialize(document)


def update_product(db, product_id: str, payload: ProductUpdate) -> dict:
    """
    Partially update a product — only fields the client explicitly sent are changed.

    model_dump() turns the Pydantic model into a dict. Fields the client didn't
    send default to None. The comprehension filters those out so $set only
    touches fields that were actually provided — sending {"price": 39.99}
    won't accidentally wipe out product_name or available_quantity.
    """
    oid = parse_object_id(product_id)

    # Keep only fields that were actually provided (non-None)
    fields_to_update = {k: v for k, v in payload.model_dump().items() if v is not None}

    if not fields_to_update:
        abort(400, description="Request body must contain at least one field to update")

    fields_to_update["updated_at"] = _now()

    # find_one_and_update atomically finds, updates, and returns the document.
    # return_document=True returns the version AFTER the update so the response
    # reflects what was actually saved, not the old values
    result = db.products.find_one_and_update(
        {"_id": oid},
        {"$set": fields_to_update},
        return_document=True,
    )

    if result is None:
        logger.warning("Product not found for update: id=%s", product_id)
        abort(404, description="Product not found")

    logger.info("Product updated: id=%s fields=%s", product_id, list(fields_to_update.keys()))
    return _serialize(result)


def delete_product(db, product_id: str) -> dict:
    """Delete a product and return the deleted document as confirmation."""
    oid = parse_object_id(product_id)
    # find_one_and_delete atomically finds and removes in one operation.
    # Returning the deleted document lets the client confirm exactly what was removed.
    doc = db.products.find_one_and_delete({"_id": oid})
    if doc is None:
        logger.warning("Product not found for deletion: id=%s", product_id)
        abort(404, description="Product not found")
    logger.info("Product deleted: id=%s", product_id)
    return _serialize(doc)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

# Why a pipeline instead of fetching all products and calculating in Python?
# If the database had 1 million products, fetching them all into memory just
# to compute an average would be extremely slow and wasteful. MongoDB is
# purpose-built for this — the pipeline runs entirely inside the database
# and returns one pre-computed result document regardless of collection size.
#
# $facet is the key operator — it runs multiple independent sub-pipelines
# in a single pass over the collection. Without $facet you'd need to query
# the database once per calculation (one for totals, one per category, etc.).
_ANALYTICS_PIPELINE = [
    {
        "$facet": {
            # Sub-pipeline A: produces one document of global totals across all products
            "summary": [
                {
                    "$group": {
                        "_id": None,                    # None means group ALL documents together
                        "total_products": {"$sum": 1},  # count every document
                        "overall_avg_price": {"$avg": "$price"},
                        "total_inventory_value": {
                            # multiply price × quantity per product, then sum across all products
                            "$sum": {"$multiply": ["$price", "$available_quantity"]}
                        },
                    }
                }
            ],
            # Sub-pipeline B: produces one document per category
            "by_category": [
                {
                    "$group": {
                        "_id": "$product_category",  # group by this field — one bucket per unique category
                        "count": {"$sum": 1},
                        "avg_price": {"$avg": "$price"},
                        "total_quantity": {"$sum": "$available_quantity"},
                        "min_price": {"$min": "$price"},
                        "max_price": {"$max": "$price"},
                    }
                },
                {"$sort": {"count": -1}},  # most products first — index 0 will be the most popular
                {
                    # $project reshapes the output — rename fields and drop _id
                    "$project": {
                        "_id": 0,                       # drop the internal _id field
                        "category": "$_id",             # rename _id → category
                        "product_count": "$count",      # rename count → product_count
                        "avg_price": "$avg_price",
                        "total_quantity": 1,            # 1 = include this field as-is
                        "min_price": 1,
                        "max_price": 1,
                    }
                },
            ],
        }
    },
    # $facet wraps each sub-pipeline result in an array even if there's only one document.
    # This second $project flattens those arrays to pull out the values directly.
    {
        "$project": {
            "total_products": {"$arrayElemAt": ["$summary.total_products", 0]},
            "overall_avg_price": {"$arrayElemAt": ["$summary.overall_avg_price", 0]},
            "total_inventory_value": {"$arrayElemAt": ["$summary.total_inventory_value", 0]},
            "most_popular_category": {
                # by_category is sorted descending by count, so index 0 is the top category
                "$arrayElemAt": ["$by_category.category", 0]
            },
            "by_category": 1,
        }
    },
]


def get_analytics(db) -> dict:
    """Run the aggregation pipeline and return a single analytics summary document."""
    results = list(db.products.aggregate(_ANALYTICS_PIPELINE))

    # $facet always returns one document even on an empty collection, but the
    # arrays inside will be empty and total_products will be missing.
    # Return explicit zero defaults so the response shape is always consistent.
    if not results or not results[0].get("total_products"):
        return {
            "total_products": 0,
            "overall_avg_price": 0.0,
            "total_inventory_value": 0.0,
            "most_popular_category": None,
            "by_category": [],
        }

    data = results[0]
    data.setdefault("most_popular_category", None)

    # Rounding is done here in Python rather than inside the pipeline with $round
    # because mongomock (used in tests) doesn't support $round in aggregations
    data["overall_avg_price"] = round(data.get("overall_avg_price") or 0, 2)
    data["total_inventory_value"] = round(data.get("total_inventory_value") or 0, 2)
    for cat in data.get("by_category", []):
        cat["avg_price"] = round(cat.get("avg_price") or 0, 2)

    return data
