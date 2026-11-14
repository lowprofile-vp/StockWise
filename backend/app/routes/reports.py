import csv
import io

from flask import Blueprint, Response, g, jsonify, request

from app.services.report_service import build_report
from app.utils.auth import login_required

bp = Blueprint("reports", __name__)

REPORTS = [
    "inventory",
    "low-stock",
    "critical",
    "sales",
    "wastage",
    "suppliers",
    "restocking",
    "purchase-orders",
    "forecast",
]


@bp.get("/reports/<report_name>")
@login_required
def report(report_name):
    payload = build_report(report_name, g.business.business_id, request.args)
    columns = [{"key": key, "label": label} for key, label in payload["columns"]]
    rows = payload["rows"]
    if (request.args.get("format") or "json").lower() == "csv":
        return _csv(report_name, columns, rows)
    return jsonify({"data": {"title": payload["title"], "columns": columns, "rows": rows}})


def _csv(name, columns, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([column["label"] for column in columns])
    for row in rows:
        writer.writerow(["" if row.get(column["key"]) is None else row.get(column["key"]) for column in columns])
    filename = f"stockwise-{name}.csv"
    return Response(
        "\ufeff" + buffer.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
