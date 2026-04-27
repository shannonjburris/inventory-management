from flask import Blueprint, jsonify, request, abort
from pydantic import ValidationError  # used by _validate helper

from app.extensions import get_db
from app.models.product import ProductCreate, ProductUpdate
from app.services import product_service
from app.services.product_service import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

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

    silent=True — return None instead of raising an exception on malformed JSON.
    Omitting force=True means Flask requires Content-Type: application/json,
    rejecting form-encoded or plain-text bodies before they reach Pydantic.
    """
    body = request.get_json(silent=True)
    if body is None:
        abort(400, description="Request body must be valid JSON with Content-Type: application/json")
    return body


def _validate(model_class, body):
    """
    Run Pydantic validation and convert ValidationError into a 400 abort.
    Centralises the try/except so each route stays to a single line.
    exc.errors() returns every failure at once — clients fix all problems in one round trip.
    """
    try:
        return model_class.model_validate(body)
    except ValidationError as exc:
        abort(400, description=exc.errors())


# ---------------------------------------------------------------------------
# Flask's router (Werkzeug) ranks routes by specificity, not registration order.
# Static segments like /analytics always take precedence over variable segments
# like /<product_id>, so route order here does not affect behavior.
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
    """GET /products — return paginated products, or search via ?search=<query>."""
    db = get_db()
    query = request.args.get("search", "").strip()
    if query:
        # Cap query length to prevent DoS via extremely large regex patterns
        if len(query) > 200:
            abort(400, description="Search query must not exceed 200 characters")
        return jsonify(product_service.search_products(db, query)), 200

    try:
        limit = int(request.args.get("limit", DEFAULT_PAGE_SIZE))
    except ValueError:
        abort(400, description="limit must be an integer")
    if not 1 <= limit <= MAX_PAGE_SIZE:
        abort(400, description=f"limit must be between 1 and {MAX_PAGE_SIZE}")

    after = request.args.get("after")
    products, next_cursor = product_service.get_all_products(db, limit=limit, after=after)
    return jsonify({"data": products, "next_cursor": next_cursor}), 200


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
    payload = _validate(ProductCreate, _parse_json_body())
    created = product_service.create_product(get_db(), payload)
    return jsonify(created), 201  # 201 Created is the correct status for a successful POST


@products_bp.route("/<product_id>", methods=["PUT"])
def update_product(product_id: str):
    """PUT /products/<id> — partially update an existing product."""
    payload = _validate(ProductUpdate, _parse_json_body())
    updated = product_service.update_product(get_db(), product_id, payload)
    return jsonify(updated), 200


@products_bp.route("/<product_id>", methods=["DELETE"])
def delete_product(product_id: str):
    """DELETE /products/<id> — delete a product and return it as confirmation."""
    db = get_db()
    deleted = product_service.delete_product(db, product_id)
    return jsonify({"message": "Product deleted", "product": deleted}), 200
