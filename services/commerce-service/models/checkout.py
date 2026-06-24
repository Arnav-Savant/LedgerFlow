import uuid
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TimestampMixin
from utils.enums import CheckoutStatus


class Checkout(TimestampMixin, Base):
    __tablename__ = "checkouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[CheckoutStatus] = mapped_column(
        SAEnum(CheckoutStatus, name="checkout_status", create_type=False),
        nullable=False,
        default=CheckoutStatus.PENDING,
    )
