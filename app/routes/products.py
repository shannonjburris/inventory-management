from flask import Blueprint, jsonify, request, abort
from pydantic import ValidationError

from app.extensions import get_db
from app.models.product import ProductCreate, ProductUpdate
from app.services import product_service

# Blueprint is Flask's equivalent of Express Router.
# url_prefix="/products" is applied when this blueprint is registered in the factory.
# Routes use "" instead of "/" so /products works without a trailing slash.
products_bp = Blueprint("products", __name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse_json_body():
    """
    Parse the request JSON body.
    `force=True` parses even if Content-Type header is missing.
    `silent=True` returns None instead of raising on malformed JSON.
    """
    body = request.get_json(force=True, silent=True)
    if body is None:
        abort(400, description="Request body must be valid JSON")
    return body


# ---------------------------------------------------------------------------
# Routes — order matters!
# GET /analytics must be registered BEFORE GET /<id> so Flask doesn't try
# to interpret the string "analytics" as a product ID.
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
    """GET /products — return all products."""
    db = get_db()
    products = product_service.get_all_products(db)
    return jsonify(products), 200


@products_bp.route("/<product_id>", methods=["GET"])
def get_product(product_id: str):
    """GET /products/<id> — return a single product."""
    db = get_db()
    product = product_service.get_product_by_id(db, product_id)
    return jsonify(product), 200


@products_bp.route("", methods=["POST"])
@products_bp.route("/", methods=["POST"])
def create_product():
    """POST /products — create a new product."""
    body = _parse_json_body()

    try:
        # model_validate() parses and validates the dict.
        # Raises ValidationError if any field is missing, wrong type, or out of range.
        payload = ProductCreate.model_validate(body)
    except ValidationError as exc:
        # exc.errors() returns a list of all validation problems — clients see everything at once.
        abort(400, description=exc.errors())

    db = get_db()
    created = product_service.create_product(db, payload)
    return jsonify(created), 201   # 201 Created is the correct status for a successful POST


@products_bp.route("/<product_id>", methods=["PUT"])
def update_product(product_id: str):
    """PUT /products/<id> — partially update an existing product."""
    body = _parse_json_body()

    try:
        payload = ProductUpdate.model_validate(body)
    except ValidationError as exc:
        abort(400, description=exc.errors())

    db = get_db()
    updated = product_service.update_product(db, product_id, payload)
    return jsonify(updated), 200


@products_bp.route("/<product_id>", methods=["DELETE"])
def delete_product(product_id: str):
    """DELETE /products/<id> — delete a product."""
    db = get_db()
    deleted = product_service.delete_product(db, product_id)
    return jsonify({"message": "Product deleted", "product": deleted}), 200
