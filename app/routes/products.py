from flask import Blueprint, jsonify, request, abort
from pydantic import ValidationError

from app.extensions import get_db
from app.models.product import ProductCreate, ProductUpdate
from app.services import product_service

# A Blueprint is a group of related routes that can be registered on the app.
# Keeping routes in a blueprint instead of directly on the app means this file
# is self-contained — adding or removing it from __init__.py is one line.
products_bp = Blueprint("products", __name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse_json_body():
    """
    Safely parse the JSON request body before passing it to a validator.

    force=True  — parse as JSON even if the Content-Type header is missing or wrong
    silent=True — return None instead of raising an exception on malformed JSON
    Without this, a client sending plain text or broken JSON would cause an
    unhandled exception instead of a clean 400 response.
    """
    body = request.get_json(force=True, silent=True)
    if body is None:
        abort(400, description="Request body must be valid JSON")
    return body


# ---------------------------------------------------------------------------
# Routes — order matters!
# /analytics must be registered BEFORE /<product_id>.
# Flask matches routes top to bottom — if /<product_id> came first, a request
# to /products/analytics would be treated as "get product with ID 'analytics'",
# which would return a 400 invalid ID error instead of the analytics data.
# ---------------------------------------------------------------------------

@products_bp.route("/analytics", methods=["GET"])
def get_analytics():
    """GET /products/analytics — aggregated product metrics."""
    db = get_db()
    data = product_service.get_analytics(db)
    return jsonify(data), 200


@products_bp.route("", methods=["GET"])
@products_bp.route("/", methods=["GET"])
def list_products():
    """GET /products — return all products, or search via ?search=<query>."""
    query = request.args.get("search", "").strip()
    if query:
        db = get_db()
        return jsonify(product_service.search_products(db, query)), 200
    db = get_db()
    products = product_service.get_all_products(db)
    return jsonify(products), 200


@products_bp.route("/<product_id>", methods=["GET"])
def get_product(product_id: str):
    """GET /products/<id> — return a single product by its MongoDB ID."""
    db = get_db()
    product = product_service.get_product_by_id(db, product_id)
    return jsonify(product), 200


@products_bp.route("", methods=["POST"])
@products_bp.route("/", methods=["POST"])
def create_product():
    """POST /products — create a new product."""
    body = _parse_json_body()

    try:
        # Hand the raw dict to Pydantic — it validates all fields and raises
        # ValidationError if anything is missing, the wrong type, or out of range
        payload = ProductCreate.model_validate(body)
    except ValidationError as exc:
        # exc.errors() returns every validation failure at once so the client
        # can fix all problems in one round trip rather than one at a time
        abort(400, description=exc.errors())

    db = get_db()
    created = product_service.create_product(db, payload)
    return jsonify(created), 201  # 201 Created is the correct status for a successful POST


@products_bp.route("/<product_id>", methods=["PUT"])
def update_product(product_id: str):
    """PUT /products/<id> — partially update an existing product."""
    body = _parse_json_body()

    try:
        # ProductUpdate has all optional fields — only provided fields will be updated
        payload = ProductUpdate.model_validate(body)
    except ValidationError as exc:
        abort(400, description=exc.errors())

    db = get_db()
    updated = product_service.update_product(db, product_id, payload)
    return jsonify(updated), 200


@products_bp.route("/<product_id>", methods=["DELETE"])
def delete_product(product_id: str):
    """DELETE /products/<id> — delete a product and return it as confirmation."""
    db = get_db()
    deleted = product_service.delete_product(db, product_id)
    return jsonify({"message": "Product deleted", "product": deleted}), 200
