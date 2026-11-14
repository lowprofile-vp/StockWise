"""0/1 knapsack for budget-constrained restocking.

Each product lot is one item.
- Weight w_i is the lot cost in whole currency units.
- Value v_i is the urgency score, an integer business priority.
- Capacity W is the budget in the same whole currency units.

A lot is purchased at its full cost or not at all. That matches the
workflow: approve a recommended order, or leave it out.

Recurrence
    dp[i][w] = max(
        dp[i - 1][w],                     # skip item i
        dp[i - 1][w - w_i] + v_i          # take item i, when w_i <= w
    )

The table has (n + 1) rows and (W + 1) columns.

Time complexity:  O(n * W) cell updates.
Space complexity: O(n * W). The full table is kept so the selected lots
can be recovered. The optimal value alone fits in O(W) space, but the
product list needs the extra row history (or an equivalent take-table).

Backtracking starts at dp[n][W]. If dp[i][w] differs from dp[i - 1][w],
item i was taken and the remaining budget falls by w_i. When the two cells
are equal, an optimum exists without that item, so it is skipped.

Budgets above MAX_CAPACITY are scaled so the table stays bounded, then
checked against the original costs. A normal restocking budget does not
hit this guard. The result says when scaling was used.
"""

MAX_CAPACITY = 100_000


def knapsack(items, capacity):
    if capacity < 0:
        raise ValueError("capacity cannot be negative")
    capacity = int(capacity)

    prepared = []
    for index, item in enumerate(items):
        weight = int(item["weight"])
        value = int(item["value"])
        if weight < 0 or value < 0:
            raise ValueError("weight and value must be non-negative")
        prepared.append(
            {
                **item,
                "_index": index,
                "weight": weight,
                "value": value,
                "original_weight": int(item.get("original_weight", weight)),
            }
        )

    scaled_items, scaled_capacity, factor = _scale(prepared, capacity)
    table, table_optimal = _build_table(scaled_items, scaled_capacity)
    chosen = set(_backtrack(table, scaled_items, scaled_capacity))
    selected = [scaled_items[index] for index in range(len(scaled_items)) if index in chosen]

    repaired = False
    if factor != 1:
        selected, repaired = _fit_original_budget(selected, capacity)

    selected_indexes = {item["_index"] for item in selected}
    excluded = []
    ordered_selected = []
    for item in scaled_items:
        if item["_index"] in selected_indexes:
            ordered_selected.append(item)
            item["reason"] = "Selected by the 0/1 dynamic program because it belongs to an optimal combination."
        else:
            if item["original_weight"] > capacity:
                reason = "Cost exceeds the budget."
            else:
                reason = (
                    "Not part of the optimal combination. Another set of lots has a "
                    "higher total urgency score inside the budget."
                )
            excluded.append({**item, "reason": reason})

    total_cost = sum(item["original_weight"] for item in ordered_selected)
    total_value = sum(item["value"] for item in ordered_selected)
    return {
        "selected": ordered_selected,
        "excluded": excluded,
        "total_cost": total_cost,
        "total_value": total_value,
        "remaining": capacity - total_cost,
        "optimal_value": total_value if repaired else table_optimal,
        "states_computed": (len(scaled_items) + 1) * (scaled_capacity + 1),
        "time_complexity": "O(n × W), where n is the number of lots and W is the budget in whole currency units",
        "space_complexity": "O(n × W) for the DP table used to recover the selected lots",
        "capacity": capacity,
        "scaled": factor != 1,
        "scale_factor": factor,
        "repaired": repaired,
        "explanation": (
            "Dynamic programming fills a table of the best total urgency score for every "
            "prefix of the lots and every budget from 0 through W. Backtracking reads which "
            "lots produced the best score. This is optimal for the 0/1 model. It does not "
            "place a purchase order."
        ),
    }


def _scale(items, capacity):
    if capacity <= MAX_CAPACITY:
        return items, capacity, 1
    factor = (capacity + MAX_CAPACITY - 1) // MAX_CAPACITY
    scaled = []
    for item in items:
        weight = item["original_weight"] // factor
        if item["original_weight"] > 0 and weight == 0:
            weight = 1
        scaled.append({**item, "weight": weight})
    return scaled, max(0, capacity // factor), factor


def _build_table(items, capacity):
    rows = len(items) + 1
    dp = [[0] * (capacity + 1) for _ in range(rows)]
    for i in range(1, rows):
        weight = items[i - 1]["weight"]
        value = items[i - 1]["value"]
        previous = dp[i - 1]
        current = dp[i]
        for budget in range(capacity + 1):
            best = previous[budget]
            if 0 <= weight <= budget:
                take = previous[budget - weight] + value
                if take > best:
                    best = take
            current[budget] = best
    return dp, dp[-1][capacity]


def _backtrack(dp, items, capacity):
    chosen = []
    budget = capacity
    for i in range(len(items), 0, -1):
        if dp[i][budget] != dp[i - 1][budget]:
            chosen.append(i - 1)
            budget -= items[i - 1]["weight"]
            if budget < 0:
                break
    chosen.reverse()
    return chosen


def _fit_original_budget(selected, capacity):
    """Drop weakest lots if scaling produced a set that misses the real budget."""
    repaired = False
    kept = list(selected)
    while kept and sum(item["original_weight"] for item in kept) > capacity:
        repaired = True

        def density(index):
            weight = kept[index]["original_weight"]
            if weight <= 0:
                return 0
            return kept[index]["value"] / weight

        weakest = 0
        for index in range(1, len(kept)):
            if density(index) < density(weakest):
                weakest = index
        kept.pop(weakest)
    return kept, repaired
