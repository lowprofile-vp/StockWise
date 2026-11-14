"""Purchase orders. Receiving goods updates stock through the same transaction log as sales."""

from datetime import timedelta
from decimal import Decimal

from app.errors import APIError
from app.extensions import db
from app.models import Product, PurchaseOrder, PurchaseOrderItem, Supplier, utcnow
from app.services.planning import quantize_money, quantize_qty, to_decimal
from app.services.stock_service import apply_stock_change
from app.utils.parsing import as_date, parse_date


OPEN_STATUSES = {"draft", "approved", "ordered", "partially_received"}
RECEIVABLE = {"approved", "ordered", "partially_received"}


def list_orders(business_id, args):
    query = PurchaseOrder.query.filter_by(business_id=business_id)
    status = (args.get("status") or "").strip()
    if status:
        query = query.filter_by(status=status)
    supplier_id = args.get("supplier_id")
    if supplier_id:
        query = query.filter_by(supplier_id=int(supplier_id))
    rows = query.order_by(PurchaseOrder.created_at.desc()).all()
    return [order_payload(row) for row in rows]


def get_order(business_id, order_id):
    order = PurchaseOrder.query.filter_by(business_id=business_id, order_id=order_id).first()
    if order is None:
        raise APIError("Purchase order not found.", 404)
    return order


def create_order(business, user, payload):
    supplier = Supplier.query.filter_by(
        business_id=business.business_id, supplier_id=payload["supplier_id"], is_active=True
    ).first()
    if supplier is None:
        raise APIError("Supplier not found.", 404)
    raw_items = payload.get("items") or []
    if not raw_items:
        raise APIError("Add at least one product to the purchase order.")
    order = PurchaseOrder(
        business_id=business.business_id,
        supplier_id=supplier.supplier_id,
        created_by=user.user_id,
        status="draft",
        notes=(payload.get("notes") or "").strip() or None,
        total_cost=0,
    )
    expected = parse_date(payload.get("expected_delivery"), "Expected delivery")
    order.expected_delivery = expected or (as_date(utcnow()) + timedelta(days=int(supplier.delivery_days or 0)))
    db.session.add(order)
    db.session.flush()

    seen = set()
    total = Decimal("0")
    for raw in raw_items:
        if not isinstance(raw, dict) or raw.get("product_id") in (None, ""):
            raise APIError("Each line needs a product_id.")
        product_id = int(raw["product_id"])
        if product_id in seen:
            raise APIError("Each product can appear only once on a purchase order.")
        seen.add(product_id)
        product = Product.query.filter_by(
            business_id=business.business_id, product_id=product_id, is_active=True
        ).first()
        if product is None:
            raise APIError("Product not found.", 404)
        quantity = quantize_qty(raw["quantity"])
        if quantity <= 0:
            raise APIError("Order quantity must be greater than zero.")
        if raw.get("unit_cost") in (None, ""):
            unit_cost = _link_price(product, supplier.supplier_id)
        else:
            unit_cost = quantize_money(raw["unit_cost"])
        total += quantize_money(quantity * unit_cost)
        db.session.add(
            PurchaseOrderItem(
                order_id=order.order_id,
                product_id=product.product_id,
                quantity=quantity,
                received_quantity=0,
                unit_cost=unit_cost,
            )
        )
    order.total_cost = quantize_money(total)
    approve = bool(payload.get("approve"))
    if approve:
        if user.role != "admin":
            raise APIError("Only the workspace owner can approve a purchase order.", 403)
        order.status = "approved"
        order.approved_by = user.user_id
    db.session.flush()
    return order


def update_status(order, new_status, user):
    if user.role != "admin":
        raise APIError("Only the workspace owner can change purchase order status.", 403)
    allowed = {
        "draft": {"approved", "cancelled"},
        "approved": {"ordered", "cancelled"},
        "ordered": {"cancelled"},
        "partially_received": set(),
        "received": set(),
        "cancelled": set(),
    }
    if new_status not in allowed.get(order.status, set()):
        raise APIError(f"Cannot move an order from {order.status.replace('_', ' ')} to {new_status.replace('_', ' ')}.")
    if new_status == "cancelled" and any(to_decimal(item.received_quantity) > 0 for item in order.items):
        raise APIError("This order already has received goods, so it cannot be cancelled.")
    if new_status == "approved":
        order.approved_by = user.user_id
    order.status = new_status
    return order


def receive_order(order, user, lines, received_at=None):
    if order.status not in RECEIVABLE:
        raise APIError("Approve and keep the order open before recording a delivery.")
    if not lines:
        raise APIError("Enter the quantities that arrived.")
    by_id = {item.id: item for item in order.items}
    touched = False
    for line in lines:
        if not isinstance(line, dict) or (line.get("id") in (None, "") and line.get("item_id") in (None, "")):
            raise APIError("Each receipt line needs an item id.")
        item_id = int(line.get("id") or line.get("item_id"))
        item = by_id.get(item_id)
        if item is None or item.order_id != order.order_id:
            raise APIError("Purchase order line not found.", 404)
        quantity = quantize_qty(line["quantity"])
        if quantity <= 0:
            raise APIError("Received quantity must be greater than zero.")
        remaining = quantize_qty(to_decimal(item.quantity) - to_decimal(item.received_quantity))
        if quantity > remaining:
            raise APIError(
                f"Cannot receive {quantity} of {item.product.name}. Only {remaining} {item.product.unit} remain on this order."
            )
        apply_stock_change(
            product=item.product,
            user=user,
            transaction_type="receipt",
            quantity=quantity,
            unit_price=item.unit_cost,
            reason=f"Delivery for PO-{order.order_id:04d}",
            transaction_date=received_at or utcnow(),
            reference_type="purchase_order",
            reference_id=order.order_id,
        )
        item.received_quantity = quantize_qty(to_decimal(item.received_quantity) + quantity)
        touched = True
    if not touched:
        raise APIError("No quantities were received.")
    if all(to_decimal(item.received_quantity) >= to_decimal(item.quantity) for item in order.items):
        order.status = "received"
    else:
        order.status = "partially_received"
    order.received_at = received_at or utcnow()
    return order


def order_payload(order):
    return {
        "order_id": order.order_id,
        "code": f"PO-{order.order_id:04d}",
        "supplier_id": order.supplier_id,
        "supplier_name": order.supplier.name if order.supplier else None,
        "status": order.status,
        "total_cost": order.total_cost,
        "notes": order.notes,
        "created_at": order.created_at,
        "expected_delivery": order.expected_delivery,
        "received_at": order.received_at,
        "created_by": order.creator.name if order.creator else None,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else None,
                "unit": item.product.unit if item.product else None,
                "quantity": item.quantity,
                "received_quantity": item.received_quantity,
                "remaining_quantity": quantize_qty(to_decimal(item.quantity) - to_decimal(item.received_quantity)),
                "unit_cost": item.unit_cost,
                "line_cost": quantize_money(to_decimal(item.quantity) * to_decimal(item.unit_cost)),
            }
            for item in order.items
        ],
    }


def _link_price(product, supplier_id):
    for link in product.supplier_links:
        if link.supplier_id == supplier_id:
            return quantize_money(link.purchase_price)
    return quantize_money(product.purchase_price)
