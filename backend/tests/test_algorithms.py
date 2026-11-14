from datetime import date
from decimal import Decimal

import pytest

from app.algorithms.greedy import greedy_select
from app.algorithms.inventory_map import InventoryHashMap
from app.algorithms.knapsack import knapsack
from app.algorithms.priority_queue import PriorityQueue
from app.algorithms.queue import OperationQueue
from app.algorithms.sliding_window import rolling_averages, window_average
from app.algorithms.sorting import merge_sort, quick_sort
from app.services.planning import assess_product


def test_hash_map_chains_collisions_and_resizes():
    inventory = InventoryHashMap(capacity=1)
    inventory.insert("rice", 18)
    inventory.insert("milk", 8)
    inventory.insert("rice", 20)
    assert inventory.get("rice") == 20
    assert inventory["milk"] == 8
    assert len(inventory) == 2
    assert inventory.delete("milk") is True
    assert inventory.get("milk") is None
    with pytest.raises(KeyError):
        inventory["milk"]

    growing = InventoryHashMap(capacity=2)
    for index in range(12):
        growing.insert(index, index * 10)
    assert len(growing) == 12
    assert all(growing.get(index) == index * 10 for index in range(12))


def test_priority_queue_extracts_most_urgent_first():
    queue = PriorityQueue()
    queue.insert("later", 5)
    queue.insert("now", 1)
    queue.insert("soon", 3)
    assert queue.peek() == "now"
    assert [queue.extract() for _ in range(3)] == ["now", "soon", "later"]
    with pytest.raises(IndexError):
        queue.extract()

    rebuilt = PriorityQueue()
    rebuilt.heapify([("later", 5), ("now", 1), ("soon", 3)])
    assert rebuilt.extract() == "now"


def test_operation_queue_is_fifo():
    pending = OperationQueue()
    assert pending.is_empty()
    pending.enqueue("sale")
    pending.enqueue("receipt")
    assert pending.peek() == "sale"
    assert pending.dequeue() == "sale"
    assert pending.dequeue() == "receipt"
    assert pending.is_empty()
    with pytest.raises(IndexError):
        pending.peek()


def test_sliding_window_average():
    series = [Decimal(value) for value in (1, 2, 3, 4, 5)]
    averages = rolling_averages(series, 3)
    assert averages[2] == Decimal("2")
    assert averages[-1] == Decimal("4")
    assert window_average(series, 3) == Decimal("4")


def test_merge_sort_is_stable_and_quick_sort_orders_values():
    pairs = [("a", 1), ("b", 1), ("c", 0)]
    merged = merge_sort(pairs, key=lambda item: item[1])
    assert [name for name, _score in merged] == ["c", "a", "b"]
    values = [5, 1, 4, 2, 3, 2]
    assert quick_sort(values) == [1, 2, 2, 3, 4, 5]
    assert merge_sort(values) == [1, 2, 2, 3, 4, 5]
    assert values == [5, 1, 4, 2, 3, 2]


def test_knapsack_selects_the_optimal_pair():
    items = [
        {"id": "A", "weight": 2, "value": 3},
        {"id": "B", "weight": 3, "value": 4},
        {"id": "C", "weight": 4, "value": 5},
    ]
    result = knapsack(items, 5)
    assert result["optimal_value"] == 7
    assert {item["id"] for item in result["selected"]} == {"A", "B"}
    assert result["total_cost"] == 5
    assert result["states_computed"] == 4 * 6


def test_greedy_can_miss_the_knapsack_optimum():
    items = [
        {"id": "A", "cost": Decimal("6"), "value": 7},
        {"id": "B", "cost": Decimal("5"), "value": 5},
        {"id": "C", "cost": Decimal("5"), "value": 5},
    ]
    greedy = greedy_select(items, Decimal("10"))
    assert {item["id"] for item in greedy["selected"]} == {"A"}
    assert greedy["total_value"] == 7

    optimal = knapsack(
        [{"id": item["id"], "weight": int(item["cost"]), "value": item["value"]} for item in items],
        10,
    )
    assert {item["id"] for item in optimal["selected"]} == {"B", "C"}
    assert optimal["total_value"] == 10
    assert optimal["total_value"] > greedy["total_value"]


def test_rice_stockout_is_critical_before_delivery():
    result = assess_product(
        current_stock=Decimal("18"),
        daily_demand=Decimal("6"),
        lead_time_days=4,
        minimum_stock=Decimal("25"),
        purchase_price=Decimal("42"),
        unit="kg",
        today=date(2026, 11, 1),
    )
    assert result["days_until_stockout"] == Decimal("3.00")
    assert result["reorder_point"] == Decimal("36.000")
    assert result["suggested_quantity"] == Decimal("60")
    assert result["estimated_cost"] == Decimal("2520.00")
    assert result["urgency"] == "Critical"
    assert result["stock_status"] == "Critical"
    assert "before a supplier delivery" in result["reason"]
    assert result["stockout_date"] == date(2026, 11, 4)
    assert result["urgency_score"] == 85.0


def test_high_band_covers_lead_time_but_not_safety_buffer():
    result = assess_product(
        current_stock=Decimal("26"),
        daily_demand=Decimal("10"),
        lead_time_days=1,
        minimum_stock=Decimal("5"),
        purchase_price=Decimal("10"),
        unit="kg",
        today=date(2026, 11, 1),
    )
    assert result["days_until_stockout"] == Decimal("2.60")
    assert result["urgency"] == "High"
    assert result["stock_status"] == "Healthy"
