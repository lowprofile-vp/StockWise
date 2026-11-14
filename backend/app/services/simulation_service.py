"""What-if simulations.

Every scenario copies the in-memory metrics and calls the same planning
formulas. Inventory rows and purchase orders are not updated.
"""

from decimal import Decimal

from app.errors import APIError
from app.extensions import db
from app.models import ProductSupplier, SimulationRun, Supplier
from app.services.metrics_service import build_metrics, project_metric, rank_metrics
from app.services.optimizer import optimize_budget
from app.services.planning import to_decimal
from app.utils.parsing import parse_decimal, parse_int
from app.utils.serialize import json_safe


def run_demand_spike(business, user, payload):
    percent = parse_decimal(payload.get("increase_percent"), "Demand increase", minimum=1, maximum=500)
    duration = parse_int(payload.get("duration_days"), "Duration", minimum=1, maximum=90)
    product_ids = _id_set(payload.get("product_ids"))
    all_products = bool(payload.get("all_products"))
    if not all_products and not product_ids:
        raise APIError("Select at least one product, or run the spike for every product.")
    metrics = build_metrics(business.business_id)
    multiplier = Decimal("1") + (percent / Decimal("100"))
    comparisons = []
    projected = []
    for metric in metrics:
        include = all_products or metric["product_id"] in product_ids
        after = project_metric(metric, demand_multiplier=multiplier) if include else metric
        projected.append(after)
        if include:
            comparisons.append(_comparison(metric, after, duration, multiplier))
    if product_ids and len(comparisons) != len(product_ids):
        found = {item["product_id"] for item in comparisons}
        missing = product_ids - found
        if missing:
            raise APIError("One or more selected products were not found.", 404)
    before_critical = _critical_count(metrics)
    after_critical = _critical_count(projected)
    sooner = sum(1 for row in comparisons if row["stockout_moved_earlier"])
    summary = (
        f"Demand +{percent}% for {len(comparisons)} product(s) over {duration} days. "
        f"Critical products {before_critical} → {after_critical}."
    )
    result = {
        "scenario_type": "demand_spike",
        "summary": summary,
        "note": "This simulation did not change inventory or create purchase orders.",
        "impact": {
            "increase_percent": percent,
            "duration_days": duration,
            "critical_before": before_critical,
            "critical_after": after_critical,
            "products_running_out_sooner": sooner,
        },
        "comparisons": comparisons,
        "recommendations": (
            "Place the products whose simulated stockout falls inside the supplier lead time "
            "at the top of the next real restock review."
        ),
    }
    return _store(business, user, "demand_spike", payload, result)


def run_supplier_delay(business, user, payload):
    supplier = Supplier.query.filter_by(
        business_id=business.business_id, supplier_id=int(payload.get("supplier_id") or 0)
    ).first()
    if supplier is None:
        raise APIError("Supplier not found.", 404)
    extra = parse_int(payload.get("extra_days"), "Extra delivery days", minimum=1, maximum=60)
    linked = {
        row.product_id
        for row in ProductSupplier.query.filter_by(supplier_id=supplier.supplier_id).all()
    }
    metrics = build_metrics(business.business_id)
    comparisons = []
    affected_before = 0
    affected_after = 0
    for metric in metrics:
        if metric["product_id"] not in linked:
            continue
        if metric["urgency"] == "Critical":
            affected_before += 1
        after = project_metric(metric, lead_time_days=int(supplier.delivery_days or 0) + extra)
        if after["urgency"] == "Critical":
            affected_after += 1
        comparisons.append(_comparison(metric, after, duration=None, multiplier=None))
    summary = (
        f"{supplier.name} delayed by {extra} days. {len(comparisons)} linked product(s) reassessed. "
        f"Critical among them: {affected_before} → {affected_after}."
    )
    result = {
        "scenario_type": "supplier_delay",
        "summary": summary,
        "note": "Lead times were changed only inside this simulation. Supplier records were not edited.",
        "supplier": {"supplier_id": supplier.supplier_id, "name": supplier.name, "delivery_days": supplier.delivery_days},
        "impact": {
            "extra_days": extra,
            "affected_products": len(comparisons),
            "critical_before": affected_before,
            "critical_after": affected_after,
            "runs_out_before_delayed_delivery": sum(
                1
                for row in comparisons
                if row["after"]["days_until_stockout"] is not None
                and float(row["after"]["days_until_stockout"]) <= int(supplier.delivery_days or 0) + extra
            ),
        },
        "comparisons": comparisons,
        "recommendations": (
            "If a linked product runs out before the delayed delivery, switch the order to a faster "
            "supplier or reduce portions until the shipment arrives."
        ),
    }
    stored_input = dict(payload)
    stored_input["supplier_name"] = supplier.name
    return _store(business, user, "supplier_delay", stored_input, result)


def run_budget_reduction(business, user, payload):
    original_budget = parse_decimal(payload.get("original_budget"), "Original budget", minimum=0)
    reduced_budget = parse_decimal(payload.get("reduced_budget"), "Simulated budget", minimum=0)
    metrics = build_metrics(business.business_id)
    original = optimize_budget(metrics, original_budget)
    reduced = optimize_budget(metrics, reduced_budget)
    original_ids = {item["product_id"] for item in original["dynamic_programming"]["selected"]}
    reduced_ids = {item["product_id"] for item in reduced["dynamic_programming"]["selected"]}
    lost = [
        item for item in original["dynamic_programming"]["selected"] if item["product_id"] not in reduced_ids
    ]
    gained = [
        item for item in reduced["dynamic_programming"]["selected"] if item["product_id"] not in original_ids
    ]
    summary = (
        f"Budget {original_budget} → {reduced_budget}. "
        f"Optimal lots {len(original_ids)} → {len(reduced_ids)}. "
        f"{len(lost)} lot(s) drop out of the optimal plan."
    )
    result = {
        "scenario_type": "budget_reduction",
        "summary": summary,
        "note": "No purchase order was created. Compare the plans, then approve a real order in the Restock Center.",
        "original": original,
        "simulated": reduced,
        "differences": {
            "excluded_under_simulated_budget": lost,
            "added_under_simulated_budget": gained,
        },
        "recommendations": (
            "Review excluded critical lots before accepting the smaller plan. "
            "The dynamic program maximizes total urgency score, so a single expensive critical lot "
            "can lose to several smaller lots."
        ),
    }
    return _store(business, user, "budget_reduction", payload, result)


def list_history(business_id):
    rows = (
        SimulationRun.query.filter_by(business_id=business_id)
        .order_by(SimulationRun.created_at.desc())
        .limit(40)
        .all()
    )
    return [_history_row(row) for row in rows]


def rerun(business, user, simulation_id):
    previous = SimulationRun.query.filter_by(business_id=business.business_id, simulation_id=simulation_id).first()
    if previous is None:
        raise APIError("Simulation not found.", 404)
    payload = dict(previous.input_parameters or {})
    runners = {
        "demand_spike": run_demand_spike,
        "supplier_delay": run_supplier_delay,
        "budget_reduction": run_budget_reduction,
    }
    runner = runners.get(previous.scenario_type)
    if runner is None:
        raise APIError("This simulation cannot be rerun.")
    fresh = runner(business, user, payload)
    fresh["rerun_of"] = simulation_id
    fresh["note"] = "Rerun against current inventory using the saved inputs. Earlier results were left unchanged."
    return fresh


def _store(business, user, scenario_type, payload, result):
    safe_result = json_safe(result)
    safe_input = json_safe(payload)
    row = SimulationRun(
        business_id=business.business_id,
        user_id=user.user_id,
        scenario_type=scenario_type,
        input_parameters=safe_input,
        results=safe_result,
        summary=(result.get("summary") or "")[:400],
    )
    db.session.add(row)
    db.session.flush()
    safe_result["simulation_id"] = row.simulation_id
    safe_result["created_at"] = row.created_at.isoformat()
    row.results = safe_result
    return safe_result


def _history_row(row):
    return {
        "simulation_id": row.simulation_id,
        "scenario_type": row.scenario_type,
        "summary": row.summary,
        "created_at": row.created_at,
        "input_parameters": row.input_parameters,
        "results": row.results,
    }


def _id_set(values):
    if not values:
        return set()
    if not isinstance(values, list):
        raise APIError("product_ids must be a list.")
    parsed = set()
    for value in values:
        try:
            parsed.add(int(value))
        except (TypeError, ValueError) as exc:
            raise APIError("Product ids must be whole numbers.") from exc
    return parsed


def _critical_count(metrics):
    return sum(1 for metric in metrics if metric["urgency"] == "Critical")


def _comparison(before, after, duration, multiplier):
    before_days = before.get("days_until_stockout")
    after_days = after.get("days_until_stockout")
    moved = (
        before_days is not None
        and after_days is not None
        and to_decimal(after_days) < to_decimal(before_days)
    )
    expected = None
    shortfall = None
    if duration is not None:
        expected = to_decimal(after["average_daily_demand"]) * Decimal(duration)
        shortfall = max(Decimal("0"), expected - to_decimal(after["current_stock"]))
    return {
        "product_id": before["product_id"],
        "name": before["name"],
        "unit": before["unit"],
        "stockout_moved_earlier": bool(moved),
        "expected_use": expected,
        "shortfall": shortfall,
        "before": _slice(before),
        "after": _slice(after),
    }


def _slice(metric):
    return {
        "average_daily_demand": metric.get("average_daily_demand"),
        "days_until_stockout": metric.get("days_until_stockout"),
        "stockout_date": metric.get("stockout_date"),
        "lead_time_days": metric.get("lead_time_days"),
        "urgency": metric.get("urgency"),
        "urgency_score": metric.get("urgency_score"),
        "suggested_quantity": metric.get("suggested_quantity"),
        "estimated_cost": metric.get("estimated_cost"),
        "current_stock": metric.get("current_stock"),
        "reason": metric.get("reason"),
    }


# rank_metrics is part of the public engine surface used by tests and reruns.
_ = rank_metrics
