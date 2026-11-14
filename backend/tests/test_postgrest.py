from datetime import date, datetime, time, timezone

from app.models import Product, PurchaseOrder
from app.data.api import clause_filter, param_for, query_string


def test_postgrest_eq_and_in_filters():
    kind, table, column, value = clause_filter(PurchaseOrder.business_id == 5)
    assert (kind, table, column, value) == ("eq", "purchase_orders", "business_id", 5)
    assert param_for(column, kind, value) == ("business_id", "eq.5")

    kind, table, column, value = clause_filter(PurchaseOrder.status.in_(["draft", "approved"]))
    assert (kind, table, column) == ("in", "purchase_orders", "status")
    assert param_for(column, kind, value) == ("status", 'in.("draft","approved")')

    assert param_for("supabase_uid", "eq", "550e8400-e29b-41d4-a716-446655440000") == (
        "supabase_uid",
        "eq.550e8400-e29b-41d4-a716-446655440000",
    )
    assert param_for("email", "eq", "owner@example.com") == ("email", "eq.owner@example.com")


def test_postgrest_null_and_ilike_filters():
    kind, _table, column, value = clause_filter(PurchaseOrder.expected_delivery.isnot(None))
    assert kind == "not_null"
    assert param_for(column, kind, value) == ("expected_delivery", "not.is.null")

    kind, _table, column, value = clause_filter(PurchaseOrder.expected_delivery < date(2026, 11, 10))
    assert kind == "lt"
    assert param_for(column, kind, value) == ("expected_delivery", "lt.2026-11-10")

    kind, _table, column, value = clause_filter(Product.name.ilike("%Rice%"))
    assert kind == "ilike"
    assert value == "*Rice*"
    assert param_for(column, kind, value) == ("name", "ilike.*Rice*")


def test_timezone_offset_is_not_read_as_a_space():
    moment = datetime.combine(date(2026, 10, 12), time.min, tzinfo=timezone.utc)
    rendered = query_string([("transaction_date", f"gte.{moment.isoformat()}")])
    assert rendered == "transaction_date=gte.2026-10-12T00:00:00%2B00:00"
