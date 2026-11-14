from flask import Blueprint, Response, g, jsonify, request

from app.extensions import db
from app.services.transaction_service import csv_template, import_csv, list_transactions, record_transaction, summarize
from app.services.stock_service import movement_payload
from app.utils.auth import login_required

bp = Blueprint("transactions", __name__)


@bp.get("/transactions")
@login_required
def transactions():
    rows, meta = list_transactions(g.business.business_id, request.args)
    return jsonify({"data": rows, "meta": meta})


@bp.post("/transactions")
@login_required
def add_transaction():
    entry = record_transaction(g.user, request.get_json(silent=True) or {})
    db.session.commit()
    return jsonify({"data": movement_payload(entry)}), 201


@bp.get("/transactions/summary")
@login_required
def transaction_summary():
    return jsonify({"data": summarize(g.business.business_id, request.args)})


@bp.post("/transactions/import")
@login_required
def upload_transactions():
    result = import_csv(request.files.get("file"), g.user)
    db.session.commit()
    return jsonify({"data": result})


@bp.get("/transactions/template")
@login_required
def template():
    return Response(
        csv_template(),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="stockwise-sales-template.csv"'},
    )
