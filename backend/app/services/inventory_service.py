"""Product catalog queries and edits. Stock quantity is never overwritten here."""

from datetime import timedelta

from app.algorithms.priority_queue import PriorityQueue
from app.algorithms.sorting import merge_sort, quick_sort
from app.errors import APIError
from app.extensions import db
from app.models import Category, Product, ProductSupplier, PurchaseOrder, PurchaseOrderItem, Supplier, Transaction
from app.services.metrics_service import build_metrics, rank_metrics
from app.services.planning import assess_product, quantize_money, quantize_qty, stock_status, to_decimal
from app.services.planning import rank_key
from app.services.stock_service import apply_stock_change, movement_payload
from app.utils.parsing import as_date
from app.utils.serialize import paginate, product_code


def list_categories(business_id):
    rows = Category.query.filter_by(business_id=business_id).all()
    ordered = merge_sort(rows, key=lambda row: row.name.lower())
    return [{"id": row.id, "name": row.name} for row in ordered]


def add_category(business_id, name):
    existing = Category.query.filter_by(business_id=business_id, name=name).first()
    if existing:
        return existing
    row = Category(business_id=business_id, name=name)
    db.session.add(row)
    db.session.flush()
    return row


def delete_category(business_id, category_id):
    row = Category.query.filter_by(business_id=business_id, id=category_id).first()
    if row is None:
        raise APIError("Category not found.", 404)
    used = Product.query.filter_by(business_id=business_id, category=row.name).first()
    if used:
        raise APIError("This category is still used by a product. Reassign those products first.")
    db.session.delete(row)


def create_product(business, user, payload, links=None):
    _ensure_category(business.business_id, payload["category"])
    supplier_id = payload.get("preferred_supplier_id")
    if supplier_id:
        _supplier_for(business.business_id, supplier_id)
    product = Product(
        business_id=business.business_id,
        name=payload["name"],
        category=payload["category"],
        current_stock=0,
        minimum_stock=quantize_qty(payload["minimum_stock"]),
        unit=payload["unit"],
        selling_price=quantize_money(payload["selling_price"]),
        purchase_price=quantize_money(payload["purchase_price"]),
        preferred_supplier_id=supplier_id,
        notes=payload.get("notes"),
        is_active=True,
    )
    db.session.add(product)
    db.session.flush()
    opening = quantize_qty(payload.get("current_stock") or 0)
    if opening > 0:
        apply_stock_change(
            product=product,
            user=user,
            transaction_type="opening",
            quantity=opening,
            unit_price=product.purchase_price,
            reason="Opening stock",
            transaction_date=payload.get("transaction_date"),
        )
    elif opening < 0:
        raise APIError("Opening stock cannot be negative.")
    _replace_links(product, business.business_id, links)
    return product


def update_product(product, business_id, payload, links=None):
    if "current_stock" in payload:
        incoming = quantize_qty(payload["current_stock"])
        if incoming != quantize_qty(product.current_stock):
            raise APIError("Stock changes must be recorded as inventory transactions.")
    if "category" in payload and payload["category"]:
        _ensure_category(business_id, payload["category"])
        product.category = payload["category"]
    for field in ("name", "unit", "notes"):
        if field in payload and payload[field] is not None:
            setattr(product, field, payload[field])
    if "minimum_stock" in payload:
        product.minimum_stock = quantize_qty(payload["minimum_stock"])
    if "selling_price" in payload:
        product.selling_price = quantize_money(payload["selling_price"])
    if "purchase_price" in payload:
        product.purchase_price = quantize_money(payload["purchase_price"])
    if "preferred_supplier_id" in payload:
        supplier_id = payload["preferred_supplier_id"] or None
        if supplier_id:
            _supplier_for(business_id, supplier_id)
        product.preferred_supplier_id = supplier_id
    if "is_active" in payload:
        product.is_active = bool(payload["is_active"])
    if links is not None:
        _replace_links(product, business_id, links)
    return product


def list_products(business_id, args):
    include_inactive = str(args.get("include_inactive", "")).lower() in {"1", "true", "yes"}
    metrics = build_metrics(business_id)
    by_id = {metric["product_id"]: metric for metric in metrics}
    products = Product.query.filter_by(business_id=business_id).all()
    rows = []
    for product in products:
        if not product.is_active and not include_inactive:
            continue
        metric = by_id.get(product.product_id)
        rows.append(_row_from(product, metric))

    search = (args.get("search") or "").strip().lower()
    if search:
        rows = [row for row in rows if _matches(row, search)]
    category = (args.get("category") or "").strip()
    if category:
        rows = [row for row in rows if row["category"].lower() == category.lower()]
    status = (args.get("status") or "").strip().lower()
    if status:
        rows = [row for row in rows if row["stock_status"].lower() == status]

    sort = (args.get("sort") or "name").lower()
    order = (args.get("order") or ("desc" if sort == "urgency" else "asc")).lower()
    rows = _sort_rows(rows, sort)
    if order == "desc" and sort != "urgency":
        rows = list(reversed(rows))
    if order == "asc" and sort == "urgency":
        rows = list(reversed(rows))
    page_rows, meta = paginate(rows, args.get("page", 1), args.get("per_page", 10))
    meta["sort"] = sort
    meta["order"] = order
    meta["sort_algorithm"] = {
        "name": "merge sort",
        "quantity": "quick sort",
        "price": "quick sort",
        "urgency": "min-heap priority queue",
    }.get(sort, "merge sort")
    return page_rows, meta


def get_product_detail(business_id, product_id):
    product = Product.query.filter_by(business_id=business_id, product_id=product_id).first()
    if product is None:
        raise APIError("Product not found.", 404)
    metrics = build_metrics(business_id, only_product_id=product_id) if product.is_active else []
    metric = metrics[0] if metrics else _inactive_metric(product)
    movements = (
        Transaction.query.filter_by(business_id=business_id, product_id=product_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.transaction_id.desc())
        .limit(30)
        .all()
    )
    sales = [entry for entry in movements if entry.transaction_type == "sale"]
    order_items = (
        PurchaseOrderItem.query.join(PurchaseOrder)
        .filter(PurchaseOrder.business_id == business_id, PurchaseOrderItem.product_id == product_id)
        .order_by(PurchaseOrder.created_at.desc())
        .limit(15)
        .all()
    )
    return {
        "product": _row_from(product, metric),
        "forecast": metric,
        "movements": [movement_payload(entry) for entry in movements],
        "sales": [movement_payload(entry) for entry in sales],
        "suppliers": _supplier_rows(product),
        "purchase_orders": [_order_item_row(item) for item in order_items],
    }


def _row_from(product, metric):
    base = {
        "product_id": product.product_id,
        "code": product_code(product.product_id),
        "name": product.name,
        "category": product.category,
        "current_stock": product.current_stock,
        "minimum_stock": product.minimum_stock,
        "unit": product.unit,
        "selling_price": product.selling_price,
        "purchase_price": product.purchase_price,
        "supplier_id": product.preferred_supplier_id,
        "supplier_name": product.preferred_supplier.name if product.preferred_supplier else None,
        "is_active": product.is_active,
        "notes": product.notes,
        "created_at": product.created_at,
        "stock_status": "Out of Stock" if to_decimal(product.current_stock) <= 0 else "Healthy",
        "urgency": None,
        "urgency_score": None,
        "days_until_stockout": None,
        "stockout_date": None,
        "average_daily_demand": None,
        "suggested_quantity": None,
        "estimated_cost": None,
        "reorder_point": None,
        "reason": None,
        "data_warning": None,
        "lead_time_days": None,
    }
    if metric:
        for key in (
            "supplier_id",
            "supplier_name",
            "stock_status",
            "urgency",
            "urgency_score",
            "days_until_stockout",
            "stockout_date",
            "average_daily_demand",
            "suggested_quantity",
            "estimated_cost",
            "reorder_point",
            "reason",
            "data_warning",
            "lead_time_days",
            "trend",
            "insufficient_history",
        ):
            if key in metric and metric[key] is not None:
                base[key] = metric[key]
        base["stock_status"] = metric["stock_status"]
    return base


def _inactive_metric(product):
    assessed = assess_product(
        current_stock=product.current_stock,
        daily_demand=0,
        lead_time_days=0,
        minimum_stock=product.minimum_stock,
        purchase_price=product.purchase_price,
        unit=product.unit,
    )
    assessed.update(
        {
            "product_id": product.product_id,
            "name": product.name,
            "data_warning": "This product is inactive, so demand was not forecast.",
            "insufficient_history": True,
            "trend": "unknown",
            "lead_time_days": None,
            "stock_status": stock_status(product.current_stock, product.minimum_stock, None, 9999),
        }
    )
    return assessed


def _matches(row, search):
    if search in row["name"].lower() or search in row["code"].lower():
        return True
    if search.isdigit() and int(search) == row["product_id"]:
        return True
    compact = search[3:] if search.startswith("sw-") else search
    return compact.isdigit() and int(compact) == row["product_id"]


def _sort_rows(rows, sort):
    if sort == "quantity":
        return quick_sort(rows, key=lambda row: to_decimal(row["current_stock"]))
    if sort == "price":
        return quick_sort(rows, key=lambda row: to_decimal(row["selling_price"]))
    if sort == "urgency":
        scored = []
        for row in rows:
            score = row["urgency_score"]
            placeholder = {
                "urgency_score": 0 if score is None else score,
                "days_until_stockout": row["days_until_stockout"],
            }
            scored.append((row, placeholder))
        heap = PriorityQueue()
        for index, (row, metric) in enumerate(scored):
            heap.insert(row, rank_key(metric, index))
        ordered = []
        while not heap.is_empty():
            ordered.append(heap.extract())
        return ordered
    return merge_sort(rows, key=lambda row: row["name"].lower())


def _ensure_category(business_id, name):
    found = Category.query.filter_by(business_id=business_id, name=name).first()
    if found is None:
        raise APIError(f"Create the category '{name}' before assigning it to a product.")
    return found


def _supplier_for(business_id, supplier_id):
    supplier = Supplier.query.filter_by(business_id=business_id, supplier_id=supplier_id, is_active=True).first()
    if supplier is None:
        raise APIError("Supplier not found.", 404)
    return supplier


def _replace_links(product, business_id, links):
    if links is None:
        return
    product.supplier_links.clear()
    db.session.flush()
    seen = set()
    for link in links:
        supplier_id = int(link["supplier_id"])
        if supplier_id in seen:
            continue
        seen.add(supplier_id)
        _supplier_for(business_id, supplier_id)
        product.supplier_links.append(
            ProductSupplier(
                supplier_id=supplier_id,
                purchase_price=quantize_money(link.get("purchase_price", product.purchase_price)),
                minimum_order_quantity=quantize_qty(link.get("minimum_order_quantity") or 0),
            )
        )
    if product.preferred_supplier_id and product.preferred_supplier_id not in seen and seen:
        product.preferred_supplier_id = next(iter(seen))


def _supplier_rows(product):
    rows = []
    for link in product.supplier_links:
        supplier = link.supplier
        if supplier is None:
            continue
        rows.append(
            {
                "supplier_id": supplier.supplier_id,
                "name": supplier.name,
                "phone": supplier.phone,
                "email": supplier.email,
                "delivery_days": supplier.delivery_days,
                "purchase_price": link.purchase_price,
                "minimum_order_quantity": link.minimum_order_quantity,
                "is_preferred": supplier.supplier_id == product.preferred_supplier_id,
                "is_active": supplier.is_active,
            }
        )
    return merge_sort(rows, key=lambda row: (row["delivery_days"], to_decimal(row["purchase_price"])))


def _order_item_row(item):
    order = item.order
    return {
        "order_id": order.order_id,
        "code": f"PO-{order.order_id:04d}",
        "status": order.status,
        "supplier_name": order.supplier.name if order.supplier else None,
        "quantity": item.quantity,
        "received_quantity": item.received_quantity,
        "unit_cost": item.unit_cost,
        "created_at": order.created_at,
        "expected_delivery": order.expected_delivery,
        "received_at": order.received_at,
    }


def recent_product_cutoff():
    return timedelta(days=7)
