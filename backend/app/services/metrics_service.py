"""Build restocking metrics from database rows and the DSA layer.

Product lookup uses the custom hash map. Urgency order comes from the
min-heap. Demand uses the sliding-window helpers. The database is read
first; nothing here changes stock.
"""

from datetime import datetime, time, timedelta, timezone

from app.algorithms.inventory_map import InventoryHashMap
from app.algorithms.priority_queue import PriorityQueue
from app.algorithms.sorting import merge_sort
from app.extensions import db
from app.models import Product, ProductSupplier, RestockRecommendation, Transaction, utcnow
from app.services.demand import build_daily_totals, choose_demand, compare_periods
from app.services.planning import (
    DEFAULT_LEAD_DAYS,
    assess_product,
    quantize_qty,
    rank_key,
    to_decimal,
)
from app.utils.parsing import as_date
from app.utils.serialize import product_code

ENGINE = {
    "product_lookup": "Custom hash map with separate chaining (inventory_map.py).",
    "urgency_ranking": "Min-heap priority queue (priority_queue.py). The smallest priority is the most urgent product.",
    "demand": "7-day sliding window. A 30-day average is included only when 30 calendar days exist.",
    "ordering": "Order-up-to level from lead time, a 7-day review cycle, and 2 safety days.",
    "estimate_warning": "These are estimates from recent usage, not guaranteed future demand.",
}


def build_metrics(business_id, *, today=None, only_product_id=None, persist_snapshot=False):
    today = today or datetime.now().date()
    window_start = today - timedelta(days=29)
    query = Product.query.filter_by(business_id=business_id, is_active=True)
    if only_product_id is not None:
        query = query.filter_by(product_id=only_product_id)
    products = query.all()

    product_map = InventoryHashMap()
    for product in products:
        product_map.insert(product.product_id, product)
    if len(product_map) == 0:
        return []

    ids = [product.product_id for product in products]
    start_dt = datetime.combine(window_start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(today, time.max, tzinfo=timezone.utc)
    transactions = (
        Transaction.query.filter(Transaction.business_id == business_id)
        .filter(Transaction.product_id.in_(ids))
        .filter(Transaction.transaction_date >= start_dt)
        .filter(Transaction.transaction_date <= end_dt)
        .all()
    )

    demand_map = InventoryHashMap()
    for entry in transactions:
        if entry.transaction_type not in ("sale", "consumption"):
            continue
        bucket = demand_map.get(entry.product_id)
        if bucket is None:
            bucket = []
            demand_map.insert(entry.product_id, bucket)
        bucket.append((as_date(entry.transaction_date), entry.quantity))

    links = ProductSupplier.query.filter(ProductSupplier.product_id.in_(ids)).all()
    link_map = InventoryHashMap()
    for link in links:
        bucket = link_map.get(link.product_id)
        if bucket is None:
            bucket = []
            link_map.insert(link.product_id, bucket)
        bucket.append(link)

    metrics = []
    for product in products:
        # Hash-map retrieval is the access path the rest of this loop uses.
        loaded = product_map.get(product.product_id)
        events = demand_map.get(loaded.product_id, [])
        created = as_date(loaded.created_at) or today
        start = window_start
        if events:
            first_demand = min(day for day, _quantity in events)
            start = max(window_start, min(created, first_demand))
        elif created > window_start:
            start = created
        if start > today:
            start = today
        series = build_daily_totals(events, start, today)
        demand = choose_demand(series)
        trend = compare_periods(series)
        supplier = _choose_supplier(loaded, link_map.get(loaded.product_id, []))
        assessed = assess_product(
            current_stock=loaded.current_stock,
            daily_demand=demand["average_daily_demand"],
            lead_time_days=supplier["lead"],
            minimum_stock=loaded.minimum_stock,
            purchase_price=supplier["price"],
            unit=loaded.unit,
            minimum_order_quantity=supplier["moq"],
            trend=trend["trend"],
            today=today,
        )
        warning = None
        if demand["insufficient_history"]:
            warning = (
                f"Only {demand['observed_days']} day(s) of history are available. "
                "Treat the stockout estimate as weak."
            )
        reason = assessed["reason"]
        if supplier["assumed"]:
            reason = (
                f"No supplier is linked, so a default lead time of {DEFAULT_LEAD_DAYS} days was used. "
                + reason
            )
        metrics.append(
            {
                "product_id": loaded.product_id,
                "code": product_code(loaded.product_id),
                "name": loaded.name,
                "category": loaded.category,
                "unit": loaded.unit,
                "current_stock": quantize_qty(loaded.current_stock),
                "minimum_stock": quantize_qty(loaded.minimum_stock),
                "selling_price": loaded.selling_price,
                "purchase_price": loaded.purchase_price,
                "lot_price": supplier["price"],
                "supplier_id": supplier["supplier_id"],
                "supplier_name": supplier["supplier_name"],
                "lead_time_days": supplier["lead"],
                "supplier_assumed": supplier["assumed"],
                "minimum_order_quantity": quantize_qty(supplier["moq"]),
                "is_active": loaded.is_active,
                "average_daily_demand": demand["average_daily_demand"],
                "average_7_day": demand["average_7_day"],
                "average_30_day": demand["average_30_day"],
                "observed_days": demand["observed_days"],
                "insufficient_history": demand["insufficient_history"],
                "data_warning": warning,
                "trend": trend["trend"],
                "trend_change_percent": trend["change_percent"],
                **assessed,
                "reason": reason,
            }
        )

    ranked = rank_metrics(metrics)
    if persist_snapshot:
        _save_snapshot(business_id, ranked)
    return ranked


def rank_metrics(metrics):
    """Most urgent product first, via the custom min-heap."""
    heap = PriorityQueue()
    for index, metric in enumerate(metrics):
        heap.insert(metric, rank_key(metric, index))
    ranked = []
    while not heap.is_empty():
        ranked.append(heap.extract())
    return ranked


def project_metric(metric, *, demand_multiplier=1, lead_time_days=None, extra_lead_days=0, today=None):
    """Recompute one metric with hypothetical demand or lead time. Does not write stock."""
    daily = quantize_qty(to_decimal(metric["average_daily_demand"]) * to_decimal(demand_multiplier))
    base_lead = metric["lead_time_days"] if lead_time_days is None else lead_time_days
    lead = max(0, int(base_lead) + int(extra_lead_days))
    assessed = assess_product(
        current_stock=metric["current_stock"],
        daily_demand=daily,
        lead_time_days=lead,
        minimum_stock=metric["minimum_stock"],
        purchase_price=metric.get("lot_price", metric["purchase_price"]),
        unit=metric["unit"],
        minimum_order_quantity=metric.get("minimum_order_quantity") or 0,
        trend=metric.get("trend") or "unknown",
        today=today,
    )
    projected = dict(metric)
    projected.update(assessed)
    projected["average_daily_demand"] = daily
    projected["lead_time_days"] = lead
    return projected


def _choose_supplier(product, links):
    active = []
    for link in links or []:
        supplier = link.supplier
        if supplier is None or not supplier.is_active:
            continue
        if supplier.business_id != product.business_id:
            continue
        active.append(link)
    chosen = None
    if product.preferred_supplier_id:
        for link in active:
            if link.supplier_id == product.preferred_supplier_id:
                chosen = link
                break
    if chosen is None and active:
        ordered = merge_sort(
            active,
            key=lambda link: (link.supplier.delivery_days, to_decimal(link.purchase_price)),
        )
        chosen = ordered[0]
    if chosen is None:
        return {
            "supplier_id": None,
            "supplier_name": None,
            "lead": DEFAULT_LEAD_DAYS,
            "price": product.purchase_price,
            "moq": 0,
            "assumed": True,
        }
    return {
        "supplier_id": chosen.supplier_id,
        "supplier_name": chosen.supplier.name,
        "lead": int(chosen.supplier.delivery_days or 0),
        "price": chosen.purchase_price if chosen.purchase_price is not None else product.purchase_price,
        "moq": chosen.minimum_order_quantity or 0,
        "assumed": False,
    }


def _save_snapshot(business_id, metrics):
    RestockRecommendation.query.filter_by(business_id=business_id).delete(synchronize_session=False)
    moment = utcnow()
    for metric in metrics:
        db.session.add(
            RestockRecommendation(
                product_id=metric["product_id"],
                business_id=business_id,
                urgency=metric["urgency"],
                urgency_score=metric["urgency_score"],
                suggested_quantity=metric["suggested_quantity"],
                estimated_cost=metric["estimated_cost"],
                days_until_stockout=metric["days_until_stockout"],
                reason=metric["reason"],
                generated_at=moment,
            )
        )
