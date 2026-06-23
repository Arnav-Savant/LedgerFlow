"""Initial schema — users, sellers, products, inventory, checkouts, orders

Revision ID: 0001
Revises:
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# PGEnum with create_type=False — op.execute below owns type creation.
# sa.Enum ignores create_type=False inside op.create_table in some SQLAlchemy
# versions; PGEnum respects it unconditionally.
_checkout_status = PGEnum(
    "PENDING", "PAYMENT_INITIATED", "PAYMENT_FAILED", "PAYMENT_COMPLETED", "EXPIRED", "CANCELLED",
    name="checkout_status", create_type=False,
)
_order_status = PGEnum(
    "CREATED", "PAYMENT_PENDING", "CONFIRMED", "CANCELLED", "REFUND_INITIATED", "REFUNDED",
    name="order_status", create_type=False,
)
_currency = PGEnum(
    "INR", "USD", "GBP", "EUR", "JPY",
    name="currency", create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE TYPE checkout_status AS ENUM ('PENDING', 'PAYMENT_INITIATED', 'PAYMENT_FAILED', 'PAYMENT_COMPLETED', 'EXPIRED', 'CANCELLED')")
    op.execute("CREATE TYPE order_status AS ENUM ('CREATED', 'PAYMENT_PENDING', 'CONFIRMED', 'CANCELLED', 'REFUND_INITIATED', 'REFUNDED')")
    op.execute("CREATE TYPE currency AS ENUM ('INR', 'USD', 'GBP', 'EUR', 'JPY')")

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "sellers",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("seller_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("currency", _currency, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "inventory",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("available_quantity", sa.Integer(), nullable=False),
        sa.Column("reserved_quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id"),
    )

    op.create_table(
        "checkouts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("seller_id", sa.String(36), nullable=False),
        sa.Column("coupon_id", sa.String(36), nullable=True),
        sa.Column("total_amount", sa.Integer(), nullable=False),
        sa.Column("final_amount", sa.Integer(), nullable=False),
        sa.Column("status", _checkout_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("checkout_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("seller_id", sa.String(36), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", _currency, nullable=False),
        sa.Column("order_status", _order_status, nullable=False),
        sa.Column("checkout_status", _checkout_status, nullable=False),
        sa.Column("ledger_updated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("wallet_updated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["checkout_id"], ["checkouts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_checkouts_user_id", "checkouts", ["user_id"])
    op.create_index("ix_orders_checkout_id", "orders", ["checkout_id"])
    op.create_index("ix_orders_user_id", "orders", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_index("ix_orders_checkout_id", table_name="orders")
    op.drop_index("ix_checkouts_user_id", table_name="checkouts")
    op.drop_table("orders")
    op.drop_table("checkouts")
    op.drop_table("inventory")
    op.drop_table("products")
    op.drop_table("sellers")
    op.drop_table("users")
    op.execute("DROP TYPE checkout_status")
    op.execute("DROP TYPE order_status")
    op.execute("DROP TYPE currency")
