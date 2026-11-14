"""Demo workspace for Campus Bites Canteen.

Run from the backend directory:

    python seed.py
    python seed.py --reset

The script is deterministic (random seed 42) and refuses to duplicate the
demo account unless --reset is passed. It writes through the same tables
the API uses, including an opening balance and a stock movement for every
later change.
"""

import random
import sys
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from app import create_app
from app.extensions import db
from app.models import (
    Business,
    Category,
    PasswordResetToken,
    Product,
    ProductSupplier,
    PurchaseOrder,
    PurchaseOrderItem,
    RestockRecommendation,
    SimulationRun,
    Supplier,
    Transaction,
    User,
)
from app.services.metrics_service import build_metrics
from app.services.planning import INTEGER_UNITS, quantize_qty
from app.utils.auth import hash_password

ADMIN_EMAIL = "admin@stockwise.demo"
STAFF_EMAIL = "staff@stockwise.demo"
ADMIN_PASSWORD = "Admin@12345"
STAFF_PASSWORD = "Staff@12345"


SUPPLIERS = [
    {"key": "grain", "name": "Grain and Co", "contact_person": "Order Desk", "phone": "9811001001", "email": "orders@grainandco.demo", "address": "Azadpur Mandi, Delhi", "delivery_days": 4},
    {"key": "farm", "name": "FreshFarm Produce", "contact_person": "Dispatch Desk", "phone": "9811001002", "email": "dispatch@freshfarm.demo", "address": "Okhla Sabzi Mandi, Delhi", "delivery_days": 2},
    {"key": "dairy", "name": "DairyDrop", "contact_person": "Order Desk", "phone": "9811001003", "email": "hello@dairydrop.demo", "address": "Karol Bagh, Delhi", "delivery_days": 1},
    {"key": "metro", "name": "Metro Wholesale", "contact_person": "Sales Desk", "phone": "9811001004", "email": "sales@metrowholesale.demo", "address": "Naraina, Delhi", "delivery_days": 5},
    {"key": "bakery", "name": "City Bakery Supply", "contact_person": "Order Desk", "phone": "9811001005", "email": "orders@citybakery.demo", "address": "Kamla Nagar, Delhi", "delivery_days": 1},
]

# cover_days is the stock level the demo should land on, measured in days of
# the generated demand. min_factor is minimum stock divided by that quantity.
PRODUCTS = [
    {"name": "Rice", "category": "Grains", "unit": "kg", "rate": "7.2", "cover": "3", "min_factor": "1.5", "sell": "60", "buy": "42", "supplier": "grain", "usage": "consumption", "moq": "10"},
    {"name": "Wheat Flour", "category": "Grains", "unit": "kg", "rate": "2.4", "cover": "20", "min_factor": "0.35", "sell": "45", "buy": "32", "supplier": "grain", "usage": "consumption", "moq": "10"},
    {"name": "Toor Dal", "category": "Pulses", "unit": "kg", "rate": "1.6", "cover": "5.5", "min_factor": "0.7", "sell": "140", "buy": "110", "supplier": "grain", "usage": "consumption", "moq": "5"},
    {"name": "Sugar", "category": "Grocery", "unit": "kg", "rate": "1.5", "cover": "16", "min_factor": "0.4", "sell": "48", "buy": "36", "supplier": "grain", "usage": "consumption", "moq": "5"},
    {"name": "Salt", "category": "Grocery", "unit": "kg", "rate": "0.35", "cover": "40", "min_factor": "0.2", "sell": "22", "buy": "12", "supplier": "grain", "usage": "consumption", "moq": "2"},
    {"name": "Cooking Oil", "category": "Grocery", "unit": "L", "rate": "1.3", "cover": "4", "min_factor": "1.3", "sell": "160", "buy": "130", "supplier": "metro", "usage": "consumption", "moq": "5"},
    {"name": "Tea", "category": "Beverages", "unit": "kg", "rate": "0.45", "cover": "14", "min_factor": "0.6", "sell": "420", "buy": "300", "supplier": "metro", "usage": "consumption", "moq": "1"},
    {"name": "Coffee", "category": "Beverages", "unit": "kg", "rate": "0.32", "cover": "13", "min_factor": "0.6", "sell": "600", "buy": "450", "supplier": "metro", "usage": "consumption", "moq": "1"},
    {"name": "Biscuits", "category": "Snacks", "unit": "pack", "rate": "6", "cover": "25", "min_factor": "0.35", "sell": "20", "buy": "12", "supplier": "metro", "usage": "sale", "moq": "12"},
    {"name": "Instant Noodles", "category": "Snacks", "unit": "pack", "rate": "5", "cover": "20", "min_factor": "0.35", "sell": "15", "buy": "10", "supplier": "metro", "usage": "sale", "moq": "12"},
    {"name": "Chicken", "category": "Protein", "unit": "kg", "rate": "3.1", "cover": "2.2", "min_factor": "1.8", "sell": "280", "buy": "210", "supplier": "metro", "usage": "consumption", "moq": "5"},
    {"name": "Milk", "category": "Dairy", "unit": "L", "rate": "10", "cover": "0.9", "min_factor": "2", "sell": "58", "buy": "46", "supplier": "dairy", "usage": "sale", "moq": "10"},
    {"name": "Eggs", "category": "Dairy", "unit": "pcs", "rate": "24", "cover": "12", "min_factor": "1.25", "sell": "8", "buy": "6", "supplier": "dairy", "usage": "sale", "moq": "30"},
    {"name": "Butter", "category": "Dairy", "unit": "pack", "rate": "2.2", "cover": "2.6", "min_factor": "0.45", "sell": "55", "buy": "42", "supplier": "dairy", "usage": "sale", "moq": "6"},
    {"name": "Curd", "category": "Dairy", "unit": "kg", "rate": "4", "cover": "0", "min_factor": "0", "sell": "70", "buy": "50", "supplier": "dairy", "usage": "sale", "moq": "5"},
    {"name": "Bread", "category": "Bakery", "unit": "loaf", "rate": "8", "cover": "0.6", "min_factor": "3", "sell": "40", "buy": "25", "supplier": "bakery", "usage": "sale", "moq": "10"},
    {"name": "Tomatoes", "category": "Produce", "unit": "kg", "rate": "4.2", "cover": "3.5", "min_factor": "0.7", "sell": "40", "buy": "22", "supplier": "farm", "usage": "consumption", "moq": "5"},
    {"name": "Onions", "category": "Produce", "unit": "kg", "rate": "3.2", "cover": "18", "min_factor": "0.3", "sell": "30", "buy": "16", "supplier": "farm", "usage": "consumption", "moq": "5"},
    {"name": "Potatoes", "category": "Produce", "unit": "kg", "rate": "4", "cover": "22", "min_factor": "0.3", "sell": "25", "buy": "12", "supplier": "farm", "usage": "consumption", "moq": "10"},
    {"name": "Bananas", "category": "Produce", "unit": "dozen", "rate": "2", "cover": "8", "min_factor": "0.4", "sell": "50", "buy": "30", "supplier": "farm", "usage": "sale", "moq": "2"},
]


def main():
    app = create_app()
    with app.app_context():
        if app.config.get("SUPABASE_URL") and app.config.get("SUPABASE_PUBLISHABLE_KEY"):
            print("Supabase is configured with the project URL and publishable key.")
            print("Run backend/supabase_schema.sql in the Supabase SQL editor.")
            print("Then register in the app. Staff join with the workspace code shown to the owner.")
            print("Seed does not use a database password or a service-role key.")
            return
        db.create_all()
        reset = "--reset" in sys.argv
        existing = User.query.filter_by(email=ADMIN_EMAIL).first()
        if existing and not reset:
            print("Demo data already exists. Run python seed.py --reset to rebuild it.")
            return
        if existing:
            _delete_demo()
        _build()
        db.session.commit()
        _print_summary()


def _delete_demo():
    business_ids = [row.business_id for row in Business.query.filter(Business.join_code == "CAMPUS").all()]
    user_ids = [row.user_id for row in User.query.filter(User.email.in_([ADMIN_EMAIL, STAFF_EMAIL])).all()]
    if not business_ids and not user_ids:
        return
    if business_ids:
        SimulationRun.query.filter(SimulationRun.business_id.in_(business_ids)).delete(synchronize_session=False)
        RestockRecommendation.query.filter(RestockRecommendation.business_id.in_(business_ids)).delete(synchronize_session=False)
        order_ids = [row.order_id for row in PurchaseOrder.query.filter(PurchaseOrder.business_id.in_(business_ids)).all()]
        if order_ids:
            PurchaseOrderItem.query.filter(PurchaseOrderItem.order_id.in_(order_ids)).delete(synchronize_session=False)
        PurchaseOrder.query.filter(PurchaseOrder.business_id.in_(business_ids)).delete(synchronize_session=False)
        Transaction.query.filter(Transaction.business_id.in_(business_ids)).delete(synchronize_session=False)
        product_ids = [row.product_id for row in Product.query.filter(Product.business_id.in_(business_ids)).all()]
        if product_ids:
            ProductSupplier.query.filter(ProductSupplier.product_id.in_(product_ids)).delete(synchronize_session=False)
        Product.query.filter(Product.business_id.in_(business_ids)).delete(synchronize_session=False)
        Supplier.query.filter(Supplier.business_id.in_(business_ids)).delete(synchronize_session=False)
        Category.query.filter(Category.business_id.in_(business_ids)).delete(synchronize_session=False)
        Business.query.filter(Business.business_id.in_(business_ids)).update({Business.owner_id: None}, synchronize_session=False)
        db.session.flush()
    PasswordResetToken.query.filter(PasswordResetToken.user_id.in_(user_ids)).delete(synchronize_session=False)
    User.query.filter(User.user_id.in_(user_ids)).delete(synchronize_session=False)
    if business_ids:
        Business.query.filter(Business.business_id.in_(business_ids)).delete(synchronize_session=False)
    db.session.commit()


def _build():
    created_at = _at(datetime.now().date() - timedelta(days=40), 9)
    business = Business(
        business_name="Campus Bites Canteen",
        business_type="College Canteen",
        currency="INR",
        restock_budget=Decimal("25000"),
        join_code="CAMPUS",
        setup_complete=True,
        created_at=created_at,
    )
    db.session.add(business)
    db.session.flush()
    admin = User(
        name="Demo Owner",
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        role="admin",
        business_id=business.business_id,
        created_at=created_at,
    )
    staff = User(
        name="Demo Staff",
        email=STAFF_EMAIL,
        password_hash=hash_password(STAFF_PASSWORD),
        role="staff",
        business_id=business.business_id,
        created_at=created_at,
    )
    db.session.add_all([admin, staff])
    db.session.flush()
    business.owner_id = admin.user_id

    for name in ["Grains", "Pulses", "Grocery", "Beverages", "Snacks", "Protein", "Dairy", "Bakery", "Produce"]:
        db.session.add(Category(business_id=business.business_id, name=name, created_at=created_at))
    supplier_rows = {}
    for spec in SUPPLIERS:
        row = Supplier(
            business_id=business.business_id,
            name=spec["name"],
            contact_person=spec["contact_person"],
            phone=spec["phone"],
            email=spec["email"],
            address=spec["address"],
            delivery_days=spec["delivery_days"],
            notes="Demo supplier.",
            created_at=created_at,
        )
        db.session.add(row)
        db.session.flush()
        supplier_rows[spec["key"]] = row

    today = datetime.now().date()
    window = [today - timedelta(days=offset) for offset in range(29, -1, -1)]
    rng = random.Random(42)
    plans = []
    for spec in PRODUCTS:
        daily = []
        for day in window:
            factor = Decimal("0.25") if day.weekday() == 6 else Decimal("0.75") if day.weekday() == 5 else Decimal("1")
            noise = Decimal(str(round(rng.uniform(0.9, 1.1), 3)))
            quantity = _unit_qty(Decimal(spec["rate"]) * factor * noise, spec["unit"])
            daily.append(quantity)
        average = sum(daily, Decimal("0")) / Decimal(len(daily))
        if Decimal(spec["cover"]) == 0:
            target = Decimal("0")
            minimum = _unit_qty(average * Decimal("2"), spec["unit"])
        else:
            target = _unit_qty(average * Decimal(spec["cover"]), spec["unit"])
            minimum = _unit_qty(target * Decimal(spec["min_factor"]), spec["unit"])
            if Decimal(spec["min_factor"]) > 1 and minimum <= target:
                minimum = _unit_qty(target + Decimal("1"), spec["unit"])
        product = Product(
            business_id=business.business_id,
            name=spec["name"],
            category=spec["category"],
            current_stock=0,
            minimum_stock=minimum,
            unit=spec["unit"],
            selling_price=Decimal(spec["sell"]),
            purchase_price=Decimal(spec["buy"]),
            preferred_supplier_id=supplier_rows[spec["supplier"]].supplier_id,
            created_at=created_at,
            updated_at=created_at,
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(
            ProductSupplier(
                product_id=product.product_id,
                supplier_id=supplier_rows[spec["supplier"]].supplier_id,
                purchase_price=Decimal(spec["buy"]),
                minimum_order_quantity=Decimal(spec["moq"]),
            )
        )
        plans.append({"spec": spec, "product": product, "daily": daily, "target": target, "average": average})

    db.session.flush()
    _purchase_orders(business, admin, supplier_rows, plans, window)
    _stock_history(business, admin, staff, plans, window)
    print("Seeded Campus Bites Canteen.")
    print(f"Owner  {ADMIN_EMAIL}  /  {ADMIN_PASSWORD}")
    print(f"Staff  {STAFF_EMAIL}  /  {STAFF_PASSWORD}")
    print("Workspace code  CAMPUS")


def _purchase_orders(business, admin, suppliers, plans, window):
    by_name = {plan["spec"]["name"]: plan["product"] for plan in plans}
    dairy = _order(
        business,
        admin,
        suppliers["dairy"],
        window[2],
        "received",
        [
            (by_name["Milk"], "20", "46"),
            (by_name["Eggs"], "30", "6"),
            (by_name["Butter"], "6", "42"),
        ],
        received_on=window[3],
    )
    _order(
        business,
        admin,
        suppliers["farm"],
        window[10],
        "partially_received",
        [
            (by_name["Tomatoes"], "20", "22"),
            (by_name["Onions"], "25", "16"),
        ],
        received_on=window[12],
        partial={"Tomatoes": Decimal("12"), "Onions": Decimal("25")},
    )
    _order(
        business,
        admin,
        suppliers["grain"],
        window[24],
        "ordered",
        [
            (by_name["Rice"], "50", "42"),
            (by_name["Wheat Flour"], "30", "32"),
        ],
        expected=window[24] + timedelta(days=4),
    )
    _order(
        business,
        admin,
        suppliers["metro"],
        window[27],
        "draft",
        [
            (by_name["Cooking Oil"], "15", "130"),
            (by_name["Tea"], "5", "300"),
        ],
    )
    return dairy


def _order(business, admin, supplier, created_day, status, lines, received_on=None, partial=None, expected=None):
    order = PurchaseOrder(
        business_id=business.business_id,
        supplier_id=supplier.supplier_id,
        created_by=admin.user_id,
        approved_by=admin.user_id if status != "draft" else None,
        status=status,
        total_cost=0,
        created_at=_at(created_day, 11),
        expected_delivery=expected or (created_day + timedelta(days=supplier.delivery_days)),
        received_at=_at(received_on, 16) if received_on else None,
    )
    db.session.add(order)
    db.session.flush()
    total = Decimal("0")
    for product, quantity, cost in lines:
        qty = Decimal(quantity)
        unit_cost = Decimal(cost)
        received = Decimal("0")
        if status == "received":
            received = qty
        elif partial and product.name in partial:
            received = partial[product.name]
        total += qty * unit_cost
        db.session.add(
            PurchaseOrderItem(
                order_id=order.order_id,
                product_id=product.product_id,
                quantity=qty,
                received_quantity=received,
                unit_cost=unit_cost,
            )
        )
    order.total_cost = total.quantize(Decimal("0.01"))
    db.session.flush()
    return order


def _stock_history(business, admin, staff, plans, window):
    receipts = {}
    for item in PurchaseOrderItem.query.join(PurchaseOrder).filter(PurchaseOrder.business_id == business.business_id).all():
        if item.received_quantity and item.order.received_at:
            receipts.setdefault(item.product_id, []).append(
                (_at_from(item.order.received_at), Decimal(str(item.received_quantity)), item.order.order_id, item.unit_cost)
            )

    for plan in plans:
        product = plan["product"]
        outbound = []
        for index, day in enumerate(window):
            quantity = plan["daily"][index]
            if quantity <= 0:
                continue
            outbound.append(( _at(day, 13 if plan["spec"]["usage"] == "sale" else 9), -quantity, plan["spec"]["usage"], None, product.selling_price if plan["spec"]["usage"] == "sale" else None, None))
        if product.name in {"Tomatoes", "Bread", "Milk"}:
            waste_day = window[15]
            waste_qty = _unit_qty(Decimal(plan["spec"]["rate"]) * Decimal("0.4"), product.unit)
            if waste_qty > 0:
                outbound.append((_at(waste_day, 18), -waste_qty, "wastage", "Spoiled before service", None, "End-of-day spoilage"))
        inbound = []
        for moment, quantity, order_id, cost in receipts.get(product.product_id, []):
            inbound.append((moment, quantity, "receipt", f"Delivery for PO-{order_id:04d}", cost, order_id))
        deltas = sorted(outbound + inbound, key=lambda item: item[0])
        sum_delta = sum((item[1] for item in deltas), Decimal("0"))
        opening = plan["target"] - sum_delta
        running = opening
        lowest = opening
        for item in deltas:
            running += item[1]
            lowest = min(lowest, running)
        if lowest < 0:
            opening += -lowest
            deltas.append((_at(window[-1], 21), lowest, "adjustment", "Count correction after early sales", None, "Keeps the demo's closing stock exact"))
            # lowest is negative; adding it reduces stock back to the target.
        events = [(_at(window[0], 8), opening, "opening", "Opening stock", product.purchase_price, None)] + deltas
        running = Decimal("0")
        actor = admin
        for moment, quantity, kind, reason, price, reference in events:
            if quantity == 0:
                continue
            actor = staff if actor is admin else admin
            running = quantize_qty(running + quantity)
            if running < 0:
                raise RuntimeError(f"Negative stock while seeding {product.name}")
            stored = quantity if kind == "adjustment" else abs(quantity)
            db.session.add(
                Transaction(
                    product_id=product.product_id,
                    business_id=business.business_id,
                    user_id=actor.user_id,
                    transaction_type=kind,
                    quantity=stored,
                    unit_price=price,
                    reason=reason,
                    transaction_date=moment,
                    stock_after=running,
                    reference_type="purchase_order" if kind == "receipt" else None,
                    reference_id=reference if kind == "receipt" else None,
                )
            )
        product.current_stock = running
        if running != plan["target"]:
            raise RuntimeError(f"{product.name} closed at {running}, expected {plan['target']}")


def _print_summary():
    business = Business.query.filter_by(join_code="CAMPUS").one()
    print("\nUrgency preview:")
    for metric in build_metrics(business.business_id):
        if metric["urgency"] in {"Critical", "High", "Medium"}:
            print(
                f"  {metric['urgency']:<10} {metric['name']:<16} "
                f"stock={metric['current_stock']} {metric['unit']:<5} "
                f"days={metric['days_until_stockout']} lead={metric['lead_time_days']}"
            )


def _unit_qty(quantity, unit):
    quantity = Decimal(quantity)
    if quantity <= 0:
        return Decimal("0")
    if str(unit).lower() in INTEGER_UNITS:
        return quantity.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return quantity.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def _at(day, hour):
    return datetime.combine(day, time(hour, 0), tzinfo=timezone.utc)


def _at_from(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


if __name__ == "__main__":
    main()
