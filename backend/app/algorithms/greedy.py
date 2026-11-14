"""Greedy 0/1 selection for a restocking budget.

Each candidate is a whole restock lot: take it at its estimated cost, or
leave it. The selection key is urgency value divided by cost (value density).
Lots are ranked with merge sort, then accepted while the remaining budget
can pay the full cost.

This is a heuristic. It is fast, O(n log n) because of the sort plus a
linear scan, and it can miss the combination with the highest total value.
Dynamic programming in knapsack.py solves the same 0/1 model exactly.

Space complexity: O(n) for the ranked copy and the two result lists.

Items with non-positive value are excluded. A zero cost and positive value
is free and is taken immediately. A cost above the original budget can never
fit and is excluded before the scan.
"""

from decimal import Decimal

from app.algorithms.sorting import merge_sort


def _money(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def greedy_select(items, budget):
    budget = _money(budget)
    if budget < 0:
        raise ValueError("budget cannot be negative")

    selected = []
    excluded = []
    candidates = []

    for item in items:
        cost = _money(item.get("cost", 0))
        value = Decimal(str(item.get("value", 0)))
        record = dict(item)
        record["cost"] = cost
        record["value"] = value
        if value <= 0:
            record["reason"] = "Urgency value is zero, so this lot does not improve the objective."
            excluded.append(record)
            continue
        if cost < 0:
            record["reason"] = "Cost is invalid."
            excluded.append(record)
            continue
        if cost == 0:
            selected.append(record)
            continue
        if cost > budget:
            record["reason"] = "Estimated cost is above the total budget, so this lot can never fit."
            excluded.append(record)
            continue
        density = value / cost
        record["value_density"] = density
        candidates.append(record)

    # Highest density first. Merge sort is stable, so equal densities keep
    # the incoming order (callers pre-sort by urgency when they care).
    ranked = merge_sort(candidates, key=lambda lot: -lot["value_density"])

    remaining = budget
    for lot in ranked:
        if lot["cost"] <= remaining:
            selected.append(lot)
            remaining -= lot["cost"]
            lot["reason"] = "Selected because its urgency-to-cost ratio fit the remaining budget."
        else:
            lot["reason"] = "Estimated cost is above the remaining budget after higher-ratio lots were selected."
            excluded.append(lot)

    total_cost = sum((lot["cost"] for lot in selected), Decimal("0"))
    total_value = sum((lot["value"] for lot in selected), Decimal("0"))
    return {
        "selected": selected,
        "excluded": excluded,
        "total_cost": total_cost,
        "total_value": total_value,
        "remaining": budget - total_cost,
        "explanation": (
            "Lots are ranked by urgency score divided by restocking cost. "
            "A lot is taken only when its full cost still fits. This is a fast heuristic, "
            "not a guarantee of the maximum total urgency score."
        ),
    }
