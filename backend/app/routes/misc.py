from flask import Blueprint, jsonify

bp = Blueprint("misc", __name__)


@bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "stockwise"})
