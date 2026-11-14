from flask import Blueprint, g, jsonify, request

from app.errors import APIError
from app.extensions import db
from app.models import Product, ProductSupplier, PurchaseOrder, Supplier
from app.services.planning import quantize_money, quantize_qty, to_decimal
from app.utils.auth import admin_required, login_required
from app.utils.parsing import as_date, clean_text, json_body, parse_email, parse_int
from app.algorithms.sorting import merge_sort

bp = Blueprint("suppliers", __name__)


@bp.get("/suppliers")
@login_required
def suppliers():
    query = Supplier.query.filter_by(business_id=g.business.business_id)
    if str(request.args.get("include_inactive", "")).lower() not in {"1", "true", "yes"}:
        query = query.filter_by(is_active=True)
    search = (request.args.get("search") or "").strip().lower()
    rows = [_supplier_payload(row) for row in query.all()]
    if search:
        rows = [row for row in rows if search in row["name"].lower() or search in (row["email"] or "").lower()]
    rows = merge_sort(rows, key=lambda row: row["name"].lower())
    return jsonify({"data": rows})


@bp.post("/suppliers")
@admin_required
def add_supplier():
    supplier = Supplier(business_id=g.business.business_id, **_fields(json_body()))
    db.session.add(supplier)
    db.session.commit()
    return jsonify({"data": _supplier_payload(supplier)}), 201


@bp.get("/suppliers/compare")
@login_required
def compare():
    product_id = request.args.get("product_id")
    if not product_id:
        raise APIError("Choose a product to compare supplier prices.")
    product = Product.query.filter_by(business_id=g.business.business_id, product_id=int(product_id)).first()
    if product is None:
        raise APIError("Product not found.", 404)
    rows = []
    for link in product.supplier_links:
        supplier = link.supplier
        if supplier is None:
            continue
        rows.append(
            {
                "supplier_id": supplier.supplier_id,
                "name": supplier.name,
                "delivery_days": supplier.delivery_days,
                "purchase_price": link.purchase_price,
                "minimum_order_quantity": link.minimum_order_quantity,
                "is_preferred": supplier.supplier_id == product.preferred_supplier_id,
                "is_active": supplier.is_active,
                "phone": supplier.phone,
            }
        )
    rows = merge_sort(rows, key=lambda row: (to_decimal(row["purchase_price"]), row["delivery_days"]))
    return jsonify({"data": {"product_id": product.product_id, "name": product.name, "suppliers": rows}})


@bp.get("/suppliers/<int:supplier_id>")
@login_required
def supplier_detail(supplier_id):
    supplier = _get(supplier_id)
    return jsonify({"data": _supplier_payload(supplier, detailed=True)})


@bp.put("/suppliers/<int:supplier_id>")
@admin_required
def edit_supplier(supplier_id):
    supplier = _get(supplier_id)
    for key, value in _fields(json_body(), partial=True).items():
        setattr(supplier, key, value)
    db.session.commit()
    return jsonify({"data": _supplier_payload(supplier)})


@bp.delete("/suppliers/<int:supplier_id>")
@admin_required
def deactivate_supplier(supplier_id):
    supplier = _get(supplier_id)
    supplier.is_active = False
    db.session.commit()
    return jsonify({"message": f"{supplier.name} was deactivated."})


@bp.post("/suppliers/<int:supplier_id>/products")
@admin_required
def link_product(supplier_id):
    supplier = _get(supplier_id)
    data = json_body()
    product = Product.query.filter_by(business_id=g.business.business_id, product_id=int(data.get("product_id") or 0)).first()
    if product is None:
        raise APIError("Product not found.", 404)
    price = quantize_money(data.get("purchase_price", product.purchase_price))
    moq = quantize_qty(data.get("minimum_order_quantity") or 0)
    link = ProductSupplier.query.filter_by(product_id=product.product_id, supplier_id=supplier.supplier_id).first()
    if link is None:
        link = ProductSupplier(product_id=product.product_id, supplier_id=supplier.supplier_id, purchase_price=price, minimum_order_quantity=moq)
        db.session.add(link)
    else:
        link.purchase_price = price
        link.minimum_order_quantity = moq
    if product.preferred_supplier_id is None:
        product.preferred_supplier_id = supplier.supplier_id
    db.session.commit()
    return jsonify({"message": "Supplier linked to the product."})


@bp.delete("/suppliers/<int:supplier_id>/products/<int:product_id>")
@admin_required
def unlink_product(supplier_id, product_id):
    link = (
        ProductSupplier.query.join(Product)
        .filter(
            Product.business_id == g.business.business_id,
            ProductSupplier.supplier_id == supplier_id,
            ProductSupplier.product_id == product_id,
        )
        .first()
    )
    if link is None:
        raise APIError("That supplier is not linked to this product.", 404)
    product = link.product
    db.session.delete(link)
    if product.preferred_supplier_id == supplier_id:
        product.preferred_supplier_id = None
    db.session.commit()
    return jsonify({"message": "Supplier unlinked."})


def _get(supplier_id):
    supplier = Supplier.query.filter_by(business_id=g.business.business_id, supplier_id=supplier_id).first()
    if supplier is None:
        raise APIError("Supplier not found.", 404)
    return supplier


def _fields(data, partial=False):
    fields = {}
    if not partial or "name" in data:
        fields["name"] = clean_text(data.get("name"), "Supplier name", maximum=150)
    if "contact_person" in data:
        fields["contact_person"] = clean_text(data.get("contact_person"), "Contact person", required=False, maximum=120)
    if "phone" in data:
        fields["phone"] = clean_text(data.get("phone"), "Phone", required=False, maximum=40)
    if "email" in data and data.get("email"):
        fields["email"] = parse_email(data.get("email"))
    elif "email" in data:
        fields["email"] = None
    if "address" in data:
        fields["address"] = clean_text(data.get("address"), "Address", required=False, maximum=400)
    if not partial or "delivery_days" in data:
        fields["delivery_days"] = parse_int(data.get("delivery_days", 3), "Delivery days", minimum=0, maximum=90)
    if "notes" in data:
        fields["notes"] = clean_text(data.get("notes"), "Notes", required=False, maximum=500)
    if "is_active" in data:
        fields["is_active"] = bool(data.get("is_active"))
    return fields


def _supplier_payload(supplier, detailed=False):
    links = ProductSupplier.query.filter_by(supplier_id=supplier.supplier_id).all()
    products = []
    for link in links:
        if link.product and link.product.business_id == supplier.business_id:
            products.append(
                {
                    "product_id": link.product_id,
                    "name": link.product.name,
                    "purchase_price": link.purchase_price,
                    "minimum_order_quantity": link.minimum_order_quantity,
                    "unit": link.product.unit,
                }
            )
    payload = {
        "supplier_id": supplier.supplier_id,
        "name": supplier.name,
        "contact_person": supplier.contact_person,
        "phone": supplier.phone,
        "email": supplier.email,
        "address": supplier.address,
        "delivery_days": supplier.delivery_days,
        "notes": supplier.notes,
        "is_active": supplier.is_active,
        "products": products,
    }
    if not detailed:
        return payload
    orders = (
        PurchaseOrder.query.filter_by(business_id=supplier.business_id, supplier_id=supplier.supplier_id)
        .order_by(PurchaseOrder.created_at.desc())
        .all()
    )
    received = [order for order in orders if order.received_at and order.expected_delivery]
    on_time = 0
    delay_total = 0
    for order in received:
        delay = (as_date(order.received_at) - order.expected_delivery).days
        delay_total += delay
        if delay <= 0:
            on_time += 1
    payload["performance"] = {
        "orders": len(orders),
        "received_orders": len(received),
        "on_time_rate": round((on_time / len(received)) * 100, 1) if received else None,
        "average_delay_days": round(delay_total / len(received), 1) if received else None,
    }
    payload["orders"] = [
        {
            "order_id": order.order_id,
            "code": f"PO-{order.order_id:04d}",
            "status": order.status,
            "total_cost": order.total_cost,
            "created_at": order.created_at,
            "expected_delivery": order.expected_delivery,
            "received_at": order.received_at,
        }
        for order in orders[:20]
    ]
    return payload
