import uuid
from sqlalchemy import String, Integer, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TimestampMixin
from utils.enums import OrderStatus, CheckoutStatus, Currency


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    checkout_id: Mapped[str] = mapped_column(String(36), ForeignKey("checkouts.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False)
    seller_id: Mapped[str] = mapped_column(String(36), ForeignKey("sellers.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer(), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", create_type=False), nullable=False
    )
    order_status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status", create_type=False),
        nullable=False,
        default=OrderStatus.CREATED,
    )
    checkout_status: Mapped[CheckoutStatus] = mapped_column(
        SAEnum(CheckoutStatus, name="checkout_status", create_type=False),
        nullable=False,
    )
    ledger_updated: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    wallet_updated: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
