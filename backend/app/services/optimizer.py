"""Turn restock metrics into a budget plan using greedy selection and 0/1 knapsack.

Both methods see the same lots. Cost and budget are whole currency units so
the dynamic-programming table has an integer capacity. A lot is one
recommended order: take all of it, or none of it.
"""

from decimal import Decimal, ROUND_HALF_UP

from app.algorithms.greedy import greedy_select
from app.algorithms.knapsack import knapsack
from app.algorithms.sorting import merge_sort
from app.services.planning import formula_documentation, quantize_money, to_decimal


def optimize_budget(recommendations, budget):
    budget = quantize_money(budget)
    if budget < 0:
        from app.errors import APIError

        raise APIError("Budget cannot be negative.")
    budget_units = int(budget.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    lots = []
    skipped = []
    for recommendation in recommendations:
        lot = _lot(recommendation)
        if lot is None:
            skipped.append(_skipped(recommendation))
            continue
        lots.append(lot)

    # Stable density sort in greedy_select keeps this urgency order on ties.
    lots = merge_sort(lots, key=lambda lot: -lot["value"])
    greedy = greedy_select(lots, Decimal(budget_units))
    optimal = knapsack(
        [
            {
                **lot,
                "weight": int(lot["cost"]),
                "original_weight": int(lot["cost"]),
                "value": int(lot["value"]),
            }
            for lot in lots
        ],
        budget_units,
    )

    greedy_view = _view(greedy, skipped)
    optimal_view = _view(optimal, skipped)
    greedy_ids = {item["product_id"] for item in greedy_view["selected"]}
    optimal_ids = {item["product_id"] for item in optimal_view["selected"]}
    critical_lots = [lot for lot in lots if lot["urgency"] == "Critical"]
    critical_cost = sum((lot["cost"] for lot in critical_lots), Decimal("0"))

    return {
        "budget": Decimal(budget_units),
        "entered_budget": budget,
        "currency_rounding": "Selection uses whole currency units so the knapsack capacity is an integer.",
        "objective": (
            "Maximize the total urgency score of whole restock lots without exceeding the budget. "
            "A critical product can be left out when other lots produce a higher combined score."
        ),
        "formula": formula_documentation(),
        "greedy": greedy_view,
        "dynamic_programming": optimal_view,
        "comparison": {
            "same_selection": greedy_ids == optimal_ids,
            "greedy_value": greedy_view["total_value"],
            "optimal_value": optimal_view["total_value"],
            "value_gap": to_decimal(optimal_view["total_value"]) - to_decimal(greedy_view["total_value"]),
            "only_greedy": sorted(greedy_ids - optimal_ids),
            "only_optimal": sorted(optimal_ids - greedy_ids),
            "critical_lot_count": len(critical_lots),
            "critical_lot_cost": critical_cost,
            "budget_covers_all_critical": Decimal(budget_units) >= critical_cost,
            "note": (
                "Greedy is a fast heuristic based on urgency divided by cost. "
                "Dynamic programming finds an optimal combination for this 0/1 model. "
                "Neither result creates a purchase order."
            ),
        },
        "skipped": skipped,
    }


def _lot(recommendation):
    quantity = to_decimal(recommendation.get("suggested_quantity"))
    exact_cost = quantize_money(recommendation.get("estimated_cost"))
    value = int(round(float(recommendation.get("urgency_score") or 0)))
    if quantity <= 0 or exact_cost <= 0 or value <= 0:
        return None
    weight = int(exact_cost.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if weight <= 0:
        weight = 1
    return {
        "id": recommendation["product_id"],
        "product_id": recommendation["product_id"],
        "name": recommendation["name"],
        "unit": recommendation["unit"],
        "suggested_quantity": quantity,
        "cost": Decimal(weight),
        "exact_cost": exact_cost,
        "value": value,
        "urgency": recommendation["urgency"],
        "urgency_score": recommendation["urgency_score"],
        "supplier_id": recommendation.get("supplier_id"),
        "supplier_name": recommendation.get("supplier_name"),
        "days_until_stockout": recommendation.get("days_until_stockout"),
        "reason_for_recommendation": recommendation.get("reason"),
    }


def _skipped(recommendation):
    return {
        "product_id": recommendation["product_id"],
        "name": recommendation["name"],
        "urgency": recommendation.get("urgency"),
        "suggested_quantity": recommendation.get("suggested_quantity"),
        "estimated_cost": recommendation.get("estimated_cost"),
        "reason": "No paid restock lot is recommended for the current stock and demand.",
    }


def _view(result, skipped):
    selected = [_public(item) for item in result["selected"]]
    excluded = [_public(item) for item in result["excluded"]]
    excluded.extend(skipped)
    return {
        "selected": selected,
        "excluded": excluded,
        "total_cost": result["total_cost"],
        "total_value": result["total_value"],
        "remaining": result["remaining"],
        "explanation": result["explanation"],
        "optimal_value": result.get("optimal_value", result["total_value"]),
        "states_computed": result.get("states_computed"),
        "time_complexity": result.get("time_complexity"),
        "space_complexity": result.get("space_complexity"),
        "scaled": result.get("scaled", False),
    }


def _public(item):
    return {
        "product_id": item.get("product_id", item.get("id")),
        "name": item.get("name"),
        "unit": item.get("unit"),
        "suggested_quantity": item.get("suggested_quantity"),
        "cost": item.get("cost", item.get("original_weight")),
        "exact_cost": item.get("exact_cost"),
        "value": item.get("value"),
        "urgency": item.get("urgency"),
        "urgency_score": item.get("urgency_score"),
        "supplier_id": item.get("supplier_id"),
        "supplier_name": item.get("supplier_name"),
        "days_until_stockout": item.get("days_until_stockout"),
        "reason": item.get("reason"),
    }
