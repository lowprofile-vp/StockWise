from flask import Blueprint, g, jsonify, request

from app.errors import APIError
from app.extensions import db
from app.models import Product
from app.services.inventory_service import (
    create_product,
    get_product_detail,
    list_products,
    update_product,
)
from app.utils.auth import admin_required, login_required
from app.utils.parsing import clean_text, json_body, parse_decimal

bp = Blueprint("products", __name__)


@bp.get("/products")
@login_required
def products():
    rows, meta = list_products(g.business.business_id, request.args)
    return jsonify({"data": rows, "meta": meta})


@bp.post("/products")
@admin_required
def add_product():
    data = json_body()
    product = create_product(g.business, g.user, _product_payload(data, creating=True), _links(data))
    db.session.commit()
    return jsonify({"data": get_product_detail(g.business.business_id, product.product_id)["product"]}), 201


@bp.get("/products/<int:product_id>")
@login_required
def product_detail(product_id):
    return jsonify({"data": get_product_detail(g.business.business_id, product_id)})


@bp.put("/products/<int:product_id>")
@admin_required
def edit_product(product_id):
    product = Product.query.filter_by(business_id=g.business.business_id, product_id=product_id).first()
    if product is None:
        raise APIError("Product not found.", 404)
    data = json_body()
    update_product(product, g.business.business_id, _product_payload(data, creating=False), _links(data) if "supplier_links" in data else None)
    db.session.commit()
    return jsonify({"data": get_product_detail(g.business.business_id, product.product_id)["product"]})


@bp.delete("/products/<int:product_id>")
@admin_required
def remove_product(product_id):
    product = Product.query.filter_by(business_id=g.business.business_id, product_id=product_id).first()
    if product is None:
        raise APIError("Product not found.", 404)
    product.is_active = False
    db.session.commit()
    return jsonify({"message": f"{product.name} was deactivated. Its history is still available."})


def _product_payload(data, creating):
    payload = {}
    if creating or "name" in data:
        payload["name"] = clean_text(data.get("name"), "Product name", maximum=150)
    if creating or "category" in data:
        payload["category"] = clean_text(data.get("category"), "Category", maximum=80)
    if creating or "unit" in data:
        payload["unit"] = clean_text(data.get("unit") or "unit", "Unit", maximum=20)
    if creating or "minimum_stock" in data:
        payload["minimum_stock"] = parse_decimal(data.get("minimum_stock", 0), "Minimum stock", minimum=0)
    if creating or "selling_price" in data:
        payload["selling_price"] = parse_decimal(data.get("selling_price", 0), "Selling price", minimum=0)
    if creating or "purchase_price" in data:
        payload["purchase_price"] = parse_decimal(data.get("purchase_price", 0), "Purchase price", minimum=0)
    if creating or "current_stock" in data:
        payload["current_stock"] = parse_decimal(data.get("current_stock", 0), "Current stock", minimum=0)
    if "notes" in data:
        notes = data.get("notes")
        payload["notes"] = clean_text(notes, "Notes", required=False, maximum=500) if notes else None
    if "preferred_supplier_id" in data:
        payload["preferred_supplier_id"] = data.get("preferred_supplier_id") or None
    if "is_active" in data:
        payload["is_active"] = bool(data.get("is_active"))
    return payload


def _links(data):
    if "supplier_links" not in data or data.get("supplier_links") is None:
        return None
    links = data.get("supplier_links")
    if not isinstance(links, list):
        raise APIError("supplier_links must be a list.")
    cleaned = []
    for link in links:
        if not isinstance(link, dict) or not link.get("supplier_id"):
            raise APIError("Each supplier link needs a supplier_id.")
        cleaned.append(
            {
                "supplier_id": int(link["supplier_id"]),
                "purchase_price": link.get("purchase_price", data.get("purchase_price", 0)),
                "minimum_order_quantity": link.get("minimum_order_quantity") or 0,
            }
        )
    return cleaned
