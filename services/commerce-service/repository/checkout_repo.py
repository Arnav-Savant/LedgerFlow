import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from models.checkout import Checkout
from config.logger import logger
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
            logger.info("Checkout record created", checkout_id=checkout.id, user_id=user_id)
            return checkout
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to create checkout", user_id=user_id, error=str(e))
            raise DatabaseException(message="Failed to create checkout", details=str(e))

    def get_by_id(self, db: Session, checkout_id: str) -> Checkout:
        try:
            logger.debug("Fetching checkout by id", checkout_id=checkout_id)
            checkout = db.query(Checkout).filter(Checkout.id == checkout_id).first()
            if checkout is None:
                logger.warning("Checkout not found", checkout_id=checkout_id)
                raise NotFoundException(message=f"Checkout {checkout_id} not found")
            return checkout
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error("Failed to fetch checkout by id", checkout_id=checkout_id, error=str(e))
            raise DatabaseException(message="Failed to fetch checkout by id", details=str(e))

    def get_by_user_id(self, db: Session, user_id: str) -> list[Checkout]:
        try:
            checkouts = db.query(Checkout).filter(Checkout.user_id == user_id).all()
            logger.debug("Fetched checkouts by user", user_id=user_id, count=len(checkouts))
            return checkouts
        except SQLAlchemyError as e:
            logger.error("Failed to fetch checkouts by user", user_id=user_id, error=str(e))
            raise DatabaseException(message="Failed to fetch checkouts by user", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Checkout]:
        try:
            checkouts = db.query(Checkout).offset(skip).limit(limit).all()
            logger.debug("Fetched all checkouts", count=len(checkouts))
            return checkouts
        except SQLAlchemyError as e:
            logger.error("Failed to fetch checkouts", error=str(e))
            raise DatabaseException(message="Failed to fetch checkouts", details=str(e))

    def count_all(self, db: Session) -> int:
        try:
            return db.query(Checkout).count()
        except SQLAlchemyError as e:
            logger.error("Failed to count records", error=str(e))
            raise DatabaseException(message="Failed to count records", details=str(e))

    def set_payment_session(
        self,
        db: Session,
        checkout_id: str,
        payment_session_id: str,
    ) -> Checkout:
        try:
            checkout = self.get_by_id(db, checkout_id)
            checkout.payment_session_id = payment_session_id
            db.flush()
            db.refresh(checkout)
            logger.info("Checkout payment_session_id set", checkout_id=checkout_id, payment_session_id=payment_session_id)
            return checkout
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to set payment_session_id on checkout", checkout_id=checkout_id, error=str(e))
            raise DatabaseException(message="Failed to set payment session on checkout", details=str(e))

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
            logger.info("Checkout updated", checkout_id=checkout_id, total_amount=total_amount, status=status)
            return checkout
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to update checkout", checkout_id=checkout_id, error=str(e))
            raise DatabaseException(message="Failed to update checkout", details=str(e))

    def update_status(self, db: Session, checkout_id: str, status: CheckoutStatus) -> Checkout:
        try:
            checkout = self.get_by_id(db, checkout_id)
            checkout.status = status
            db.flush()
            db.refresh(checkout)
            logger.info("Checkout status updated", checkout_id=checkout_id, status=status)
            return checkout
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to update checkout status", checkout_id=checkout_id, error=str(e))
            raise DatabaseException(message="Failed to update checkout status", details=str(e))

    def delete(self, db: Session, checkout_id: str) -> None:
        try:
            checkout = self.get_by_id(db, checkout_id)
            db.delete(checkout)
            db.flush()
            logger.info("Checkout deleted", checkout_id=checkout_id)
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to delete checkout", checkout_id=checkout_id, error=str(e))
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
