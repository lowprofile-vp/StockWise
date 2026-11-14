from flask import Blueprint, g, jsonify

from app.extensions import db
from app.services.simulation_service import list_history, rerun, run_budget_reduction, run_demand_spike, run_supplier_delay
from app.utils.auth import login_required
from app.utils.parsing import json_body

bp = Blueprint("simulations", __name__)


@bp.post("/simulations/demand-spike")
@login_required
def demand_spike():
    result = run_demand_spike(g.business, g.user, json_body())
    db.session.commit()
    return jsonify({"data": result})


@bp.post("/simulations/supplier-delay")
@login_required
def supplier_delay():
    result = run_supplier_delay(g.business, g.user, json_body())
    db.session.commit()
    return jsonify({"data": result})


@bp.post("/simulations/budget-reduction")
@login_required
def budget_reduction():
    result = run_budget_reduction(g.business, g.user, json_body())
    db.session.commit()
    return jsonify({"data": result})


@bp.get("/simulations/history")
@login_required
def history():
    return jsonify({"data": list_history(g.business.business_id)})


@bp.post("/simulations/<int:simulation_id>/rerun")
@login_required
def rerun_simulation(simulation_id):
    result = rerun(g.business, g.user, simulation_id)
    db.session.commit()
    return jsonify({"data": result})
