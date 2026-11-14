"""SQLAlchemy models. PostgreSQL is the source of truth for every business workspace."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(512), nullable=False)
    supabase_uid = db.Column(db.String(36), unique=True, index=True)
    role = db.Column(db.String(20), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.business_id"), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    business = db.relationship("Business", foreign_keys=[business_id], back_populates="members")

    __table_args__ = (CheckConstraint("role IN ('admin', 'staff')", name="ck_users_role"),)


class Business(db.Model):
    __tablename__ = "businesses"

    business_id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(150), nullable=False)
    business_type = db.Column(db.String(80), nullable=False, default="Retail")
    currency = db.Column(db.String(8), nullable=False, default="INR")
    # Integer reference to users.user_id. A database-level FK would cycle with
    # users.business_id (businesses must exist before users, and the owner row
    # exists only after the user is inserted). The application sets both ids
    # in the same transaction.
    owner_id = db.Column(db.Integer, nullable=True, index=True)
    restock_budget = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    join_code = db.Column(db.String(12), nullable=False, unique=True, index=True)
    setup_complete = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    members = db.relationship("User", foreign_keys=[User.business_id], back_populates="business")
    owner = db.relationship("User", primaryjoin="Business.owner_id==User.user_id", foreign_keys=[owner_id])

    __table_args__ = (CheckConstraint("restock_budget >= 0", name="ck_business_budget_nonneg"),)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.business_id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (UniqueConstraint("business_id", "name", name="uq_category_business_name"),)


class Supplier(db.Model):
    __tablename__ = "suppliers"

    supplier_id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.business_id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    email = db.Column(db.String(255))
    address = db.Column(db.Text)
    delivery_days = db.Column(db.Integer, nullable=False, default=3)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (CheckConstraint("delivery_days >= 0", name="ck_suppliers_delivery_nonneg"),)


class Product(db.Model):
    __tablename__ = "products"

    product_id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.business_id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    current_stock = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    minimum_stock = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    unit = db.Column(db.String(20), nullable=False, default="unit")
    selling_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    purchase_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    preferred_supplier_id = db.Column(
        db.Integer, db.ForeignKey("suppliers.supplier_id", ondelete="SET NULL"), nullable=True
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    preferred_supplier = db.relationship("Supplier", foreign_keys=[preferred_supplier_id])
    supplier_links = db.relationship("ProductSupplier", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("current_stock >= 0", name="ck_products_stock_nonneg"),
        CheckConstraint("minimum_stock >= 0", name="ck_products_minimum_nonneg"),
        CheckConstraint("selling_price >= 0", name="ck_products_selling_nonneg"),
        CheckConstraint("purchase_price >= 0", name="ck_products_purchase_nonneg"),
    )


class ProductSupplier(db.Model):
    __tablename__ = "product_suppliers"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.supplier_id", ondelete="CASCADE"), nullable=False)
    purchase_price = db.Column(db.Numeric(12, 2), nullable=False)
    minimum_order_quantity = db.Column(db.Numeric(12, 3), nullable=False, default=0)

    product = db.relationship("Product", back_populates="supplier_links")
    supplier = db.relationship("Supplier")

    __table_args__ = (
        UniqueConstraint("product_id", "supplier_id", name="uq_product_supplier"),
        CheckConstraint("purchase_price >= 0", name="ck_link_price_nonneg"),
        CheckConstraint("minimum_order_quantity >= 0", name="ck_link_moq_nonneg"),
        Index("ix_product_suppliers_product", "product_id"),
        Index("ix_product_suppliers_supplier", "supplier_id"),
    )


class Transaction(db.Model):
    __tablename__ = "transactions"

    transaction_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.business_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2))
    reason = db.Column(db.String(200))
    notes = db.Column(db.String(500))
    transaction_date = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    stock_after = db.Column(db.Numeric(12, 3), nullable=False)
    reference_type = db.Column(db.String(40))
    reference_id = db.Column(db.Integer)

    product = db.relationship("Product")
    user = db.relationship("User")

    __table_args__ = (
        CheckConstraint("quantity != 0", name="ck_transactions_quantity_nonzero"),
        CheckConstraint(
            "transaction_type IN ('sale', 'consumption', 'wastage', 'adjustment', 'receipt', 'opening')",
            name="ck_transactions_type",
        ),
        Index("ix_transactions_business_date", "business_id", "transaction_date"),
        Index("ix_transactions_product_date", "product_id", "transaction_date"),
    )


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"

    order_id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.business_id"), nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.supplier_id"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="draft")
    total_cost = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expected_delivery = db.Column(db.Date)
    received_at = db.Column(db.DateTime(timezone=True))

    supplier = db.relationship("Supplier")
    items = db.relationship("PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan")
    creator = db.relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'approved', 'ordered', 'partially_received', 'received', 'cancelled')",
            name="ck_purchase_orders_status",
        ),
        CheckConstraint("total_cost >= 0", name="ck_purchase_orders_total_nonneg"),
    )


class PurchaseOrderItem(db.Model):
    __tablename__ = "purchase_order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("purchase_orders.order_id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    received_quantity = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False)

    order = db.relationship("PurchaseOrder", back_populates="items")
    product = db.relationship("Product")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_po_item_qty_positive"),
        CheckConstraint("received_quantity >= 0", name="ck_po_item_received_nonneg"),
        CheckConstraint("received_quantity <= quantity", name="ck_po_item_received_within_ordered"),
        CheckConstraint("unit_cost >= 0", name="ck_po_item_cost_nonneg"),
        Index("ix_po_items_order", "order_id"),
    )


class RestockRecommendation(db.Model):
    __tablename__ = "restock_recommendations"

    recommendation_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.business_id"), nullable=False, index=True)
    urgency = db.Column(db.String(20), nullable=False)
    urgency_score = db.Column(db.Numeric(6, 2), nullable=False)
    suggested_quantity = db.Column(db.Numeric(12, 3), nullable=False)
    estimated_cost = db.Column(db.Numeric(12, 2), nullable=False)
    days_until_stockout = db.Column(db.Numeric(8, 2))
    reason = db.Column(db.Text)
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class SimulationRun(db.Model):
    __tablename__ = "simulation_runs"

    simulation_id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.business_id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    scenario_type = db.Column(db.String(40), nullable=False)
    input_parameters = db.Column(db.JSON, nullable=False)
    results = db.Column(db.JSON, nullable=False)
    summary = db.Column(db.String(400))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
