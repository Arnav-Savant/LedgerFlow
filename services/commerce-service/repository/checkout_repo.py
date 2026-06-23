import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from models.checkout import Checkout
from utils.enums import CheckoutStatus
from utils.common.custom_exception import DatabaseException, NotFoundException


class CheckoutRepo:
    def create(
        self,
        db: Session,
        user_id: str,
        product_id: str,
        seller_id: str,
        total_amount: int,
        final_amount: int,
        coupon_id: Optional[str] = None,
    ) -> Checkout:
        try:
            checkout = Checkout(
                id=str(uuid.uuid4()),
                user_id=user_id,
                product_id=product_id,
                seller_id=seller_id,
                coupon_id=coupon_id,
                total_amount=total_amount,
                final_amount=final_amount,
                status=CheckoutStatus.PENDING,
            )
            db.add(checkout)
            db.commit()
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

    def update_status(self, db: Session, checkout_id: str, status: CheckoutStatus) -> Checkout:
        try:
            checkout = self.get_by_id(db, checkout_id)
            checkout.status = status
            db.commit()
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
            db.commit()
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to delete checkout", details=str(e))

    def get_with_product_and_user(self, db: Session, checkout_id: str) -> Optional[dict]:
        try:
            sql = text("""
                SELECT
                    c.id            AS checkout_id,
                    c.status        AS checkout_status,
                    c.total_amount,
                    c.final_amount,
                    u.name          AS user_name,
                    u.email         AS user_email,
                    p.name          AS product_name,
                    p.price         AS product_price,
                    s.name          AS seller_name
                FROM checkouts c
                JOIN users    u ON u.id = c.user_id
                JOIN products p ON p.id = c.product_id
                JOIN sellers  s ON s.id = c.seller_id
                WHERE c.id = :checkout_id
            """)
            row = db.execute(sql, {"checkout_id": checkout_id}).mappings().first()
            return dict(row) if row else None
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch checkout with details", details=str(e))


checkout_repo = CheckoutRepo()
