import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from models.base import Base, TimestampMixin
from utils.enums import PaymentStatus, PaymentMethod, Currency


class PaymentSession(TimestampMixin, Base):
    __tablename__ = "payment_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Cross-service reference — no DB-level FK constraint; commerce owns the checkout row
    checkout_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Cross-service reference — no DB-level FK constraint; commerce owns the user row
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    amount: Mapped[str] = mapped_column(Integer, nullable=False)

    currency: Mapped[str] = mapped_column(
        PGEnum(Currency, name="currency", create_type=False),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        PGEnum(PaymentStatus, name="payment_status", create_type=False),
        nullable=False,
        default=PaymentStatus.INITIATED,
    )

    payment_method: Mapped[Optional[str]] = mapped_column(
        PGEnum(PaymentMethod, name="payment_method", create_type=False),
        nullable=True,
    )

    redirect_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
