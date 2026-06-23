import uuid
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TimestampMixin


class Inventory(TimestampMixin, Base):
    __tablename__ = "inventory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False, unique=True)
    available_quantity: Mapped[int] = mapped_column(Integer(), nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
