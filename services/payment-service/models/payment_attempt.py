import uuid
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from models.base import Base, TimestampMixin
from utils.enums import AttemptStatus, PaymentMethod


class PaymentAttempt(TimestampMixin, Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        UniqueConstraint("session_id", "idempotency_key", name="uq_attempt_session_idempotency"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("payment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        PGEnum(PaymentMethod, name="payment_method", create_type=False),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        PGEnum(AttemptStatus, name="attempt_status", create_type=False),
        nullable=False,
        default=AttemptStatus.PENDING,
    )
    psp_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
