import uuid
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TimestampMixin
from utils.enums import Currency


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id: Mapped[str] = mapped_column(String(36), ForeignKey("sellers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(Integer(), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", create_type=False), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
