"""Atomic stock changes.

Every quantity change writes a transaction in the same database session.
The caller commits. A failure rolls the stock change and the transaction
row back together.
"""

from decimal import Decimal

from app.errors import APIError
from app.extensions import db
from app.models import Transaction, utcnow
from app.services.planning import quantize_money, quantize_qty
from app.utils.parsing import as_date


OUTBOUND = {"sale", "consumption", "wastage"}
INBOUND = {"receipt", "opening"}


def lock_product(product_id):
    from app.models import Product

    query = db.session.query(Product).filter(Product.product_id == product_id)
    bind = db.session.get_bind()
    if bind is not None and bind.dialect.name != "sqlite":
        query = query.with_for_update()
    product = query.one_or_none()
    if product is None:
        raise APIError("Product not found.", 404)
    return product


def apply_stock_change(
    *,
    product,
    user,
    transaction_type,
    quantity,
    unit_price=None,
    reason=None,
    notes=None,
    transaction_date=None,
    reference_type=None,
    reference_id=None,
):
    if product.business_id != user.business_id:
        raise APIError("Product not found.", 404)
    if transaction_type not in OUTBOUND | INBOUND | {"adjustment"}:
        raise APIError("Unknown transaction type.")

    amount = quantize_qty(quantity)
    if amount == 0:
        raise APIError("Quantity must not be zero.")

    if transaction_type in OUTBOUND or transaction_type in INBOUND:
        if amount < 0:
            raise APIError("Quantity must be greater than zero.")
        delta = -amount if transaction_type in OUTBOUND else amount
        stored_quantity = amount
    else:
        delta = amount
        stored_quantity = amount

    if not product.is_active and transaction_type != "opening":
        raise APIError(f"{product.name} is inactive. Reactivate it before recording stock movement.")

    from app.data.api import enabled

    if enabled():
        return _apply_remote(
            product=product,
            user=user,
            transaction_type=transaction_type,
            quantity=stored_quantity,
            unit_price=quantize_money(unit_price) if unit_price is not None else None,
            reason=reason,
            notes=notes,
            transaction_date=transaction_date or utcnow(),
            reference_type=reference_type,
            reference_id=reference_id,
        )

    locked = lock_product(product.product_id)
    new_stock = quantize_qty(Decimal(str(locked.current_stock)) + delta)
    if new_stock < 0:
        raise APIError(
            f"Not enough stock for {locked.name}. Available: {quantize_qty(locked.current_stock)} {locked.unit}.",
            409,
        )

    locked.current_stock = new_stock
    locked.updated_at = utcnow()
    moment = transaction_date or utcnow()
    entry = Transaction(
        product_id=locked.product_id,
        business_id=locked.business_id,
        user_id=user.user_id,
        transaction_type=transaction_type,
        quantity=stored_quantity,
        unit_price=quantize_money(unit_price) if unit_price is not None else None,
        reason=reason,
        notes=notes,
        transaction_date=moment,
        stock_after=new_stock,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.session.add(entry)
    db.session.flush()
    return entry


def _apply_remote(
    *,
    product,
    user,
    transaction_type,
    quantity,
    unit_price,
    reason,
    notes,
    transaction_date,
    reference_type,
    reference_id,
):
    from app.data.api import ApiRecord, call_rpc, current_uow

    payload = call_rpc(
        "apply_stock_change",
        {
            "p_product_id": int(product.product_id),
            "p_transaction_type": transaction_type,
            "p_quantity": format(quantity, "f"),
            "p_unit_price": None if unit_price is None else format(unit_price, "f"),
            "p_reason": reason,
            "p_notes": notes,
            "p_transaction_date": transaction_date.isoformat() if transaction_date is not None else None,
            "p_reference_type": reference_type,
            "p_reference_id": reference_id,
        },
    )
    if not isinstance(payload, dict):
        raise APIError("Supabase did not record the stock change.", 502)
    from app.models import Transaction

    entry = ApiRecord(Transaction, payload, persisted=True, track=False)
    entry._rels["product"] = product
    entry._rels["user"] = user
    stock_after = entry.stock_after
    if isinstance(product, ApiRecord):
        product.current_stock = stock_after
    cached = current_uow().identity.get(("products", product.product_id))
    if isinstance(cached, ApiRecord):
        cached.current_stock = stock_after
    return entry


def signed_quantity(transaction):
    """Quantity leaving stock is negative for display of adjustments and outbound types."""
    amount = quantize_qty(transaction.quantity)
    if transaction.transaction_type == "adjustment":
        return amount
    if transaction.transaction_type in OUTBOUND:
        return -abs(amount)
    return abs(amount)


def movement_payload(transaction, product_name=None, unit=None):
    return {
        "transaction_id": transaction.transaction_id,
        "product_id": transaction.product_id,
        "product_name": product_name or (transaction.product.name if transaction.product else None),
        "unit": unit or (transaction.product.unit if transaction.product else None),
        "transaction_type": transaction.transaction_type,
        "quantity": transaction.quantity,
        "signed_quantity": signed_quantity(transaction),
        "unit_price": transaction.unit_price,
        "reason": transaction.reason,
        "notes": transaction.notes,
        "transaction_date": transaction.transaction_date,
        "stock_after": transaction.stock_after,
        "user_name": transaction.user.name if transaction.user else None,
        "date": as_date(transaction.transaction_date).isoformat() if transaction.transaction_date else None,
    }
