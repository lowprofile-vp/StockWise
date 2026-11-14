from decimal import Decimal

from flask import Blueprint, g, jsonify

from app.errors import APIError
from app.extensions import db
from app.models import User
from app.services.inventory_service import add_category, create_product, delete_category, list_categories
from app.utils.auth import admin_required, hash_password, login_required, uses_supabase
from app.utils.parsing import clean_text, json_body, parse_decimal, parse_email, parse_password
from app.utils.serialize import user_payload

bp = Blueprint("business", __name__)

BUSINESS_TYPES = ["Grocery", "College Canteen", "Retail", "Restaurant", "Other"]


@bp.get("/business")
@login_required(allow_incomplete=True)
def get_business():
    return jsonify({"data": _business_payload(g.business, include_code=g.user.role == "admin")})


@bp.put("/business")
@admin_required
def update_business():
    data = json_body()
    if "business_name" in data:
        g.business.business_name = clean_text(data.get("business_name"), "Business name", minimum=2, maximum=150)
    if "business_type" in data:
        g.business.business_type = clean_text(data.get("business_type"), "Business type", maximum=80)
    if "currency" in data:
        g.business.currency = _currency(data.get("currency"))
    if "restock_budget" in data:
        g.business.restock_budget = parse_decimal(data.get("restock_budget"), "Restocking budget", minimum=0)
    db.session.commit()
    return jsonify({"data": _business_payload(g.business, include_code=True)})


@bp.post("/business/setup")
@login_required(allow_incomplete=True)
def setup_business():
    if g.user.role != "admin":
        raise APIError("Only the workspace owner can finish setup.", 403)
    if g.business.setup_complete:
        raise APIError("Setup is already complete. Change details in business settings.", 409)
    data = json_body()
    g.business.business_name = clean_text(data.get("business_name") or g.business.business_name, "Business name", minimum=2)
    g.business.business_type = clean_text(data.get("business_type") or "Retail", "Business type", maximum=80)
    g.business.currency = _currency(data.get("currency") or "INR")
    g.business.restock_budget = parse_decimal(data.get("restock_budget", 0), "Restocking budget", minimum=0)
    names = data.get("categories") or ["General"]
    if not isinstance(names, list) or not names:
        names = ["General"]
    for name in names:
        add_category(g.business.business_id, clean_text(name, "Category", maximum=80))
    products = data.get("products") or []
    if not isinstance(products, list):
        raise APIError("Products must be a list.")
    if len(products) > 100:
        raise APIError("Add at most 100 products during setup.")
    for raw in products:
        _create_from_setup(raw)
    g.business.setup_complete = True
    db.session.commit()
    return jsonify({"data": _business_payload(g.business, include_code=True), "user": user_payload(g.user, g.business)})


@bp.get("/categories")
@login_required
def categories():
    return jsonify({"data": list_categories(g.business.business_id)})


@bp.post("/categories")
@admin_required
def create_category():
    data = json_body()
    row = add_category(g.business.business_id, clean_text(data.get("name"), "Category", maximum=80))
    db.session.commit()
    return jsonify({"data": {"id": row.id, "name": row.name}}), 201


@bp.delete("/categories/<int:category_id>")
@admin_required
def remove_category(category_id):
    delete_category(g.business.business_id, category_id)
    db.session.commit()
    return jsonify({"message": "Category removed."})


@bp.get("/users")
@admin_required
def users():
    rows = User.query.filter_by(business_id=g.business.business_id).order_by(User.created_at.asc()).all()
    return jsonify(
        {
            "data": [
                {
                    "user_id": row.user_id,
                    "name": row.name,
                    "email": row.email,
                    "role": row.role,
                    "role_label": "Admin / Owner" if row.role == "admin" else "Staff / Inventory Manager",
                    "is_active": row.is_active,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        }
    )


@bp.post("/users")
@admin_required
def create_user():
    if uses_supabase():
        raise APIError(
            f"Staff choose their own password. Ask them to register and enter workspace code {g.business.join_code}.",
        )
    data = json_body()
    email = parse_email(data.get("email"))
    if User.query.filter_by(email=email).first():
        raise APIError("An account with this email already exists.", 409)
    role = data.get("role") or "staff"
    if role != "staff":
        raise APIError("New users created here are staff accounts. The workspace already has an owner.")
    name = clean_text(data.get("name"), "Full name", minimum=2, maximum=120)
    password = parse_password(data.get("password"))
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="staff",
        business_id=g.business.business_id,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"data": {"user_id": user.user_id, "name": user.name, "email": user.email, "role": user.role}}), 201


@bp.put("/users/<int:user_id>")
@admin_required
def update_user(user_id):
    user = User.query.filter_by(business_id=g.business.business_id, user_id=user_id).first()
    if user is None:
        raise APIError("User not found.", 404)
    data = json_body()
    if "is_active" in data:
        if user.user_id == g.user.user_id and not data.get("is_active"):
            raise APIError("You cannot deactivate your own account.")
        if user.role == "admin" and not data.get("is_active"):
            raise APIError("The workspace owner account stays active.")
        user.is_active = bool(data.get("is_active"))
    if data.get("name"):
        user.name = clean_text(data.get("name"), "Full name", minimum=2, maximum=120)
    db.session.commit()
    return jsonify({"data": {"user_id": user.user_id, "is_active": user.is_active, "name": user.name}})


def _business_payload(business, include_code):
    payload = {
        "business_id": business.business_id,
        "business_name": business.business_name,
        "business_type": business.business_type,
        "currency": business.currency,
        "restock_budget": business.restock_budget,
        "setup_complete": business.setup_complete,
        "business_types": BUSINESS_TYPES,
    }
    if include_code:
        payload["join_code"] = business.join_code
    return payload


def _currency(value):
    text = clean_text(value, "Currency", maximum=8).upper()
    if len(text) != 3 or not text.isalpha():
        raise APIError("Currency must be a 3-letter code such as INR.")
    return text


def _create_from_setup(raw):
    if not isinstance(raw, dict):
        raise APIError("Each product must be an object.")
    name = clean_text(raw.get("name"), "Product name", maximum=150)
    if not str(raw.get("name") or "").strip():
        return
    category = clean_text(raw.get("category") or "General", "Category", maximum=80)
    add_category(g.business.business_id, category)
    create_product(
        g.business,
        g.user,
        {
            "name": name,
            "category": category,
            "current_stock": parse_decimal(raw.get("current_stock", 0), "Current stock", minimum=0),
            "minimum_stock": parse_decimal(raw.get("minimum_stock", 0), "Minimum stock", minimum=0),
            "unit": clean_text(raw.get("unit") or "unit", "Unit", maximum=20),
            "selling_price": parse_decimal(raw.get("selling_price", 0), "Selling price", minimum=0),
            "purchase_price": parse_decimal(raw.get("purchase_price", 0), "Purchase price", minimum=0),
        },
    )
