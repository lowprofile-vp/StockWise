from flask import Blueprint, g, jsonify, request

from app.errors import APIError
from app.extensions import db
from app.services.metrics_service import ENGINE, build_metrics
from app.services.optimizer import optimize_budget
from app.services.planning import formula_documentation
from app.services.purchase_service import create_order, get_order, list_orders, order_payload, receive_order, update_status
from app.utils.auth import login_required
from app.utils.parsing import json_body, parse_datetime, parse_decimal

bp = Blueprint("restock", __name__)


@bp.get("/restock/recommendations")
@login_required
def recommendations():
    rows = build_metrics(g.business.business_id, persist_snapshot=True)
    db.session.commit()
    summary = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for row in rows:
        summary[row["urgency"]] = summary.get(row["urgency"], 0) + 1
    return jsonify(
        {
            "data": rows,
            "summary": summary,
            "formula": formula_documentation(),
            "engine": ENGINE,
        }
    )


@bp.post("/restock/optimize")
@login_required
def optimize():
    data = json_body()
    budget = data.get("budget", g.business.restock_budget)
    plan = optimize_budget(build_metrics(g.business.business_id), parse_decimal(budget, "Budget", minimum=0))
    plan["currency"] = g.business.currency
    return jsonify({"data": plan})


@bp.get("/restock/purchase-orders")
@login_required
def purchase_orders():
    return jsonify({"data": list_orders(g.business.business_id, request.args)})


@bp.post("/restock/purchase-orders")
@login_required
def add_purchase_order():
    order = create_order(g.business, g.user, json_body())
    db.session.commit()
    return jsonify({"data": order_payload(order)}), 201


@bp.get("/restock/purchase-orders/<int:order_id>")
@login_required
def purchase_order_detail(order_id):
    return jsonify({"data": order_payload(get_order(g.business.business_id, order_id))})


@bp.put("/restock/purchase-orders/<int:order_id>")
@login_required
def edit_purchase_order(order_id):
    data = json_body()
    status = str(data.get("status") or "").strip()
    if status not in {"draft", "approved", "ordered", "partially_received", "received", "cancelled"}:
        raise APIError("Choose a valid purchase order status.")
    order = update_status(get_order(g.business.business_id, order_id), status, g.user)
    db.session.commit()
    return jsonify({"data": order_payload(order)})


@bp.post("/restock/purchase-orders/<int:order_id>/receive")
@login_required
def receive(order_id):
    data = json_body()
    received_at = parse_datetime(data.get("received_at"), "Received date") if data.get("received_at") else None
    order = receive_order(get_order(g.business.business_id, order_id), g.user, data.get("items") or [], received_at)
    db.session.commit()
    return jsonify({"data": order_payload(order)})
