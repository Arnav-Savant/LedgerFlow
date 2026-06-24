import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from models.checkout import Checkout
from utils.enums import CheckoutStatus
from utils.common.custom_exception import DatabaseException, NotFoundException


class CheckoutRepo:
    def create(self, db: Session, user_id: str, total_amount: int = 0) -> Checkout:
        try:
            checkout = Checkout(
                id=str(uuid.uuid4()),
                user_id=user_id,
                total_amount=total_amount,
                status=CheckoutStatus.PENDING,
            )
            db.add(checkout)
            db.flush()
            db.refresh(checkout)
            return checkout
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to create checkout", details=str(e))

    def get_by_id(self, db: Session, checkout_id: str) -> Checkout:
        try:
            checkout = db.query(Checkout).filter(Checkout.id == checkout_id).first()
            if checkout is None:
                raise NotFoundException(message=f"Checkout {checkout_id} not found")
            return checkout
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch checkout by id", details=str(e))

    def get_by_user_id(self, db: Session, user_id: str) -> list[Checkout]:
        try:
            return db.query(Checkout).filter(Checkout.user_id == user_id).all()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch checkouts by user", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Checkout]:
        try:
            return db.query(Checkout).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch checkouts", details=str(e))

    def update(
        self,
        db: Session,
        checkout_id: str,
        total_amount: Optional[int] = None,
        status: Optional[CheckoutStatus] = None,
    ) -> Checkout:
        try:
            checkout = self.get_by_id(db, checkout_id)
            if total_amount is not None:
                checkout.total_amount = total_amount
            if status is not None:
                checkout.status = status
            db.flush()
            db.refresh(checkout)
            return checkout
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to update checkout", details=str(e))

    def update_status(self, db: Session, checkout_id: str, status: CheckoutStatus) -> Checkout:
        try:
            checkout = self.get_by_id(db, checkout_id)
            checkout.status = status
            db.flush()
            db.refresh(checkout)
            return checkout
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to update checkout status", details=str(e))

    def delete(self, db: Session, checkout_id: str) -> None:
        try:
            checkout = self.get_by_id(db, checkout_id)
            db.delete(checkout)
            db.flush()
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to delete checkout", details=str(e))

    def get_with_user(self, db: Session, checkout_id: str) -> Optional[dict]:
        try:
            sql = text("""
                SELECT
                    c.id            AS checkout_id,
                    c.status        AS checkout_status,
                    c.total_amount,
                    c.user_id,
                    u.name          AS user_name,
                    u.email         AS user_email
                FROM checkouts c
                JOIN users u ON u.id = c.user_id
                WHERE c.id = :checkout_id
            """)
            row = db.execute(sql, {"checkout_id": checkout_id}).mappings().first()
            return dict(row) if row else None
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch checkout with details", details=str(e))
