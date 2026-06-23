import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TimestampMixin


class Seller(TimestampMixin, Base):
    __tablename__ = "sellers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
