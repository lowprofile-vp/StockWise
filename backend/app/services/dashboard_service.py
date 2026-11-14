"""Overview numbers, charts, and notification rows. All values come from the database."""

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from app.algorithms.inventory_map import InventoryHashMap
from app.algorithms.sorting import merge_sort, quick_sort
from app.algorithms.sliding_window import rolling_averages
from app.models import Product, PurchaseOrder, Transaction
from app.services.metrics_service import ENGINE, build_metrics
from app.services.planning import quantize_money, to_decimal
from app.utils.parsing import as_date


def build_overview(business):
    today = datetime.now().date()
    metrics = build_metrics(business.business_id)
    products = Product.query.filter_by(business_id=business.business_id, is_active=True).all()
    inventory_value = sum(
        (to_decimal(product.current_stock) * to_decimal(product.purchase_price) for product in products),
        Decimal("0"),
    )
    pending = PurchaseOrder.query.filter(
        PurchaseOrder.business_id == business.business_id,
        PurchaseOrder.status.in_(["draft", "approved", "ordered", "partially_received"]),
    ).count()
    low_stock = [
        metric
        for metric in metrics
        if metric["stock_status"] in {"Low Stock", "Critical", "Out of Stock"} and metric["urgency"] != "Critical"
    ]
    critical = [metric for metric in metrics if metric["urgency"] == "Critical"]
    approaching = [metric for metric in metrics if metric["urgency"] == "High"]
    priorities = [metric for metric in metrics if to_decimal(metric["suggested_quantity"]) > 0][:5]
    return {
        "cards": {
            "total_products": len(products),
            "inventory_value": quantize_money(inventory_value),
            "low_stock_products": len(low_stock),
            "critical_stockout_risk": len(critical),
            "pending_purchase_orders": pending,
            "restock_budget": business.restock_budget,
            "currency": business.currency,
        },
        "definitions": {
            "low_stock_products": "Below or near the minimum quantity, excluding products that are already a lead-time stockout risk.",
            "critical_stockout_risk": "Out of stock, or expected to run out before the supplier lead time ends.",
            "inventory_value": "Current quantity multiplied by purchase price.",
        },
        "alerts": {
            "critical": [_alert(metric) for metric in critical[:6]],
            "low_stock": [_alert(metric) for metric in low_stock[:6]],
            "approaching_reorder": [_alert(metric) for metric in approaching[:6]],
        },
        "alert_counts": {
            "critical": len(critical),
            "low_stock": len(low_stock),
            "approaching_reorder": len(approaching),
        },
        "demand": demand_charts(business.business_id, today),
        "priorities": [_alert(metric) for metric in priorities],
        "activity": recent_activity(business.business_id),
        "trends": {
            "increasing": [metric["name"] for metric in metrics if metric["trend"] == "increasing"][:5],
            "declining": [metric["name"] for metric in metrics if metric["trend"] == "declining"][:5],
        },
        "engine": ENGINE,
    }


def demand_charts(business_id, today):
    start = today - timedelta(days=182)
    rows = _demand_rows(business_id, start, today)
    daily_map = defaultdict(lambda: Decimal("0"))
    for day, value in rows:
        daily_map[day] += value
    daily = []
    cursor = today - timedelta(days=29)
    while cursor <= today:
        daily.append({"date": cursor.isoformat(), "value": quantize_money(daily_map[cursor])})
        cursor += timedelta(days=1)
    weekly_map = defaultdict(lambda: Decimal("0"))
    month_map = defaultdict(lambda: Decimal("0"))
    cursor = today - timedelta(days=55)
    while cursor <= today:
        weekly_map[cursor - timedelta(days=cursor.weekday())] += daily_map[cursor]
        month_map[(cursor.year, cursor.month)] += daily_map[cursor]
        cursor += timedelta(days=1)
    weeks = merge_sort(list(weekly_map), key=lambda day: day.isoformat())[-8:]
    months = merge_sort(list(month_map), key=lambda key: (key[0], key[1]))[-6:]
    return {
        "daily": [{"date": point["date"], "value": point["value"]} for point in daily[-14:]],
        "weekly": [{"label": week.strftime("%d %b"), "value": quantize_money(weekly_map[week])} for week in weeks],
        "monthly": [
            {"label": datetime(year, month, 1).strftime("%b %Y"), "value": quantize_money(month_map[(year, month)])}
            for year, month in months
        ],
        "value_basis": "Sales and consumption valued at the current purchase price. Wastage is excluded.",
    }


def demand_series(business_id, *, product_id=None, category=None, start=None, end=None):
    today = datetime.now().date()
    end = end or today
    start = start or (end - timedelta(days=29))
    products = Product.query.filter_by(business_id=business_id).all()
    product_map = InventoryHashMap()
    for product in products:
        product_map.insert(product.product_id, product)
    rows = (
        Transaction.query.filter_by(business_id=business_id)
        .filter(Transaction.transaction_type.in_(["sale", "consumption"]))
        .filter(Transaction.transaction_date >= datetime.combine(start, time.min, tzinfo=timezone.utc))
        .filter(Transaction.transaction_date <= datetime.combine(end, time.max, tzinfo=timezone.utc))
        .all()
    )
    daily_value = defaultdict(lambda: Decimal("0"))
    daily_qty = defaultdict(lambda: Decimal("0"))
    product_revenue = defaultdict(lambda: Decimal("0"))
    for entry in rows:
        product = product_map.get(entry.product_id)
        if product is None:
            continue
        if product_id and product.product_id != int(product_id):
            continue
        if category and product.category.lower() != category.lower():
            continue
        day = as_date(entry.transaction_date)
        quantity = abs(to_decimal(entry.quantity))
        value = quantity * to_decimal(product.purchase_price)
        daily_value[day] += value
        daily_qty[day] += quantity
        if entry.transaction_type == "sale":
            price = entry.unit_price if entry.unit_price is not None else product.selling_price
            product_revenue[product.product_id] += quantity * to_decimal(price)
    series = []
    cursor = start
    while cursor <= end:
        series.append(daily_value[cursor])
        cursor += timedelta(days=1)
    averages = rolling_averages(series, 7) if series else []
    points = []
    cursor = start
    index = 0
    while cursor <= end:
        points.append(
            {
                "date": cursor.isoformat(),
                "value": quantize_money(daily_value[cursor]),
                "quantity": daily_qty[cursor] if product_id else None,
                "moving_average_7": quantize_money(averages[index]) if averages else None,
            }
        )
        cursor += timedelta(days=1)
        index += 1
    ranking = []
    for pid, revenue in product_revenue.items():
        product = product_map.get(pid)
        ranking.append(
            {
                "product_id": pid,
                "name": product.name,
                "unit": product.unit,
                "revenue": quantize_money(revenue),
            }
        )
    ranking = quick_sort(ranking, key=lambda row: -to_decimal(row["revenue"]))[:8]
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "mixed_units": product_id is None,
        "series": points,
        "top_products": ranking,
        "moving_average": "7-day sliding window over consumption value.",
    }


def inventory_value_trend(business_id, today=None, days=30):
    today = today or datetime.now().date()
    products = Product.query.filter_by(business_id=business_id, is_active=True).all()
    history = (
        Transaction.query.filter_by(business_id=business_id)
        .order_by(Transaction.transaction_date.asc(), Transaction.transaction_id.asc())
        .all()
    )
    by_product = defaultdict(list)
    for entry in history:
        by_product[entry.product_id].append(entry)
    start = today - timedelta(days=days - 1)
    points = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        end = datetime.combine(day, time.max, tzinfo=timezone.utc)
        total = Decimal("0")
        for product in products:
            if as_date(product.created_at) and as_date(product.created_at) > day:
                continue
            stock = Decimal("0")
            for entry in by_product.get(product.product_id, []):
                moment = entry.transaction_date
                if moment.tzinfo is None:
                    moment = moment.replace(tzinfo=timezone.utc)
                if moment <= end:
                    stock = to_decimal(entry.stock_after)
                else:
                    break
            total += stock * to_decimal(product.purchase_price)
        points.append({"date": day.isoformat(), "value": quantize_money(total)})
    return points


def recent_activity(business_id, limit=12):
    events = []
    transactions = (
        Transaction.query.filter_by(business_id=business_id)
        .order_by(Transaction.transaction_date.desc())
        .limit(20)
        .all()
    )
    for entry in transactions:
        name = entry.product.name if entry.product else "Product"
        events.append(
            {
                "kind": entry.transaction_type,
                "title": f"{entry.transaction_type.replace('_', ' ').title()} · {name}",
                "detail": f"{entry.quantity} {entry.product.unit if entry.product else ''}".strip(),
                "timestamp": entry.transaction_date,
                "href": f"/inventory/{entry.product_id}",
            }
        )
    orders = (
        PurchaseOrder.query.filter_by(business_id=business_id)
        .order_by(PurchaseOrder.created_at.desc())
        .limit(8)
        .all()
    )
    for order in orders:
        events.append(
            {
                "kind": "purchase_order",
                "title": f"Purchase order PO-{order.order_id:04d}",
                "detail": f"{order.status.replace('_', ' ')} · {order.supplier.name if order.supplier else ''}",
                "timestamp": order.created_at,
                "href": "/restock",
            }
        )
    products = (
        Product.query.filter_by(business_id=business_id)
        .order_by(Product.created_at.desc())
        .limit(5)
        .all()
    )
    for product in products:
        events.append(
            {
                "kind": "product",
                "title": f"Product added · {product.name}",
                "detail": product.category,
                "timestamp": product.created_at,
                "href": f"/inventory/{product.product_id}",
            }
        )
    ordered = merge_sort(
        events,
        key=lambda item: item["timestamp"].timestamp() if item["timestamp"] else 0,
    )
    ordered.reverse()
    trimmed = ordered[:limit]
    for index, item in enumerate(trimmed):
        item["id"] = f"{item['kind']}-{index}"
    return trimmed


def notifications_for(business):
    overview = build_overview(business)
    items = []
    for metric in overview["alerts"]["critical"]:
        items.append(
            {
                "id": f"critical-{metric['product_id']}",
                "level": "critical",
                "title": f"{metric['name']} is a stockout risk",
                "body": metric["reason"],
                "href": f"/inventory/{metric['product_id']}",
            }
        )
    for metric in overview["alerts"]["low_stock"]:
        items.append(
            {
                "id": f"low-{metric['product_id']}",
                "level": "warning",
                "title": f"{metric['name']} is low on stock",
                "body": metric["reason"],
                "href": f"/inventory/{metric['product_id']}",
            }
        )
    today = datetime.now().date()
    overdue = PurchaseOrder.query.filter(
        PurchaseOrder.business_id == business.business_id,
        PurchaseOrder.status.in_(["approved", "ordered", "partially_received"]),
        PurchaseOrder.expected_delivery.isnot(None),
        PurchaseOrder.expected_delivery < today,
    ).all()
    for order in overdue:
        items.append(
            {
                "id": f"po-{order.order_id}",
                "level": "warning",
                "title": f"PO-{order.order_id:04d} is past its expected delivery",
                "body": order.supplier.name if order.supplier else "Open the restock center to record what arrived.",
                "href": "/restock",
            }
        )
    drafts = PurchaseOrder.query.filter_by(business_id=business.business_id, status="draft").count()
    if drafts:
        items.append(
            {
                "id": "drafts",
                "level": "info",
                "title": f"{drafts} purchase order{'s' if drafts != 1 else ''} waiting for approval",
                "body": "Draft orders do not reserve stock until they are approved.",
                "href": "/restock",
            }
        )
    return items


def _alert(metric):
    return {
        "product_id": metric["product_id"],
        "code": metric.get("code"),
        "name": metric["name"],
        "unit": metric["unit"],
        "category": metric.get("category"),
        "current_stock": metric["current_stock"],
        "urgency": metric["urgency"],
        "urgency_score": metric["urgency_score"],
        "stock_status": metric["stock_status"],
        "days_until_stockout": metric["days_until_stockout"],
        "stockout_date": metric["stockout_date"],
        "lead_time_days": metric["lead_time_days"],
        "suggested_quantity": metric["suggested_quantity"],
        "estimated_cost": metric["estimated_cost"],
        "supplier_name": metric.get("supplier_name"),
        "reason": metric["reason"],
        "data_warning": metric.get("data_warning"),
        "average_daily_demand": metric.get("average_daily_demand"),
    }


def _demand_rows(business_id, start, end):
    products = {product.product_id: product for product in Product.query.filter_by(business_id=business_id).all()}
    entries = (
        Transaction.query.filter_by(business_id=business_id)
        .filter(Transaction.transaction_type.in_(["sale", "consumption"]))
        .filter(Transaction.transaction_date >= datetime.combine(start, time.min, tzinfo=timezone.utc))
        .filter(Transaction.transaction_date <= datetime.combine(end, time.max, tzinfo=timezone.utc))
        .all()
    )
    rows = []
    for entry in entries:
        product = products.get(entry.product_id)
        if product is None:
            continue
        value = abs(to_decimal(entry.quantity)) * to_decimal(product.purchase_price)
        rows.append((as_date(entry.transaction_date), value))
    return rows
