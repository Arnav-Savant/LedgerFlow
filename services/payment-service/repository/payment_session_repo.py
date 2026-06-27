import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.payment_session import PaymentSession
from config.logger import logger
from utils.common.custom_exception import DatabaseException, NotFoundException
from utils.enums import PaymentStatus, PaymentMethod


class PaymentSessionRepo:
    def create(
        self,
        db: Session,
        checkout_id: str,
        user_id: str,
        amount: int,
        currency: str,
        redirect_url: str,
        expires_at: datetime,
        payment_method: Optional[PaymentMethod] = None,
    ) -> PaymentSession:
        try:
            session = PaymentSession(
                id=str(uuid.uuid4()),
                checkout_id=checkout_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
                status=PaymentStatus.INITIATED,
                payment_method=payment_method,
                redirect_url=redirect_url,
                expires_at=expires_at,
            )
            db.add(session)
            db.flush()
            db.refresh(session)
            logger.info(
                "PaymentSession created",
                session_id=session.id,
                checkout_id=checkout_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
            )
            return session
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                "Failed to create PaymentSession",
                checkout_id=checkout_id,
                user_id=user_id,
                error=str(e),
            )
            raise DatabaseException(message="Failed to create payment session", details=str(e))

    def get_by_id(self, db: Session, session_id: str) -> PaymentSession:
        try:
            logger.debug("Fetching PaymentSession by id", session_id=session_id)
            record = db.query(PaymentSession).filter(PaymentSession.id == session_id).first()
            if record is None:
                logger.warning("PaymentSession not found", session_id=session_id)
                raise NotFoundException("PaymentSession", session_id)
            return record
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error("Failed to fetch PaymentSession by id", session_id=session_id, error=str(e))
            raise DatabaseException(message="Failed to fetch payment session by id", details=str(e))

    def get_by_checkout_id(self, db: Session, checkout_id: str) -> Optional[PaymentSession]:
        try:
            logger.debug("Fetching PaymentSession by checkout_id", checkout_id=checkout_id)
            return (
                db.query(PaymentSession)
                .filter(PaymentSession.checkout_id == checkout_id)
                .order_by(PaymentSession.created_at.desc())
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(
                "Failed to fetch PaymentSession by checkout_id",
                checkout_id=checkout_id,
                error=str(e),
            )
            raise DatabaseException(
                message="Failed to fetch payment session by checkout id", details=str(e)
            )

    def get_all_by_user_id(self, db: Session, user_id: str, skip: int = 0, limit: int = 100) -> list[PaymentSession]:
        try:
            records = (
                db.query(PaymentSession)
                .filter(PaymentSession.user_id == user_id)
                .order_by(PaymentSession.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            logger.debug("Fetched PaymentSessions for user", user_id=user_id, count=len(records))
            return records
        except SQLAlchemyError as e:
            logger.error("Failed to fetch PaymentSessions by user_id", user_id=user_id, error=str(e))
            raise DatabaseException(
                message="Failed to fetch payment sessions for user", details=str(e)
            )

    def update_status(
        self,
        db: Session,
        session_id: str,
        status: PaymentStatus,
        payment_method: Optional[PaymentMethod] = None,
    ) -> PaymentSession:
        try:
            record = self.get_by_id(db, session_id)
            old_status = record.status
            record.status = status
            if payment_method is not None:
                record.payment_method = payment_method
            db.flush()
            db.refresh(record)
            logger.info(
                "PaymentSession status updated",
                session_id=session_id,
                old_status=old_status,
                new_status=status,
            )
            return record
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                "Failed to update PaymentSession status",
                session_id=session_id,
                status=status,
                error=str(e),
            )
            raise DatabaseException(message="Failed to update payment session status", details=str(e))

    def delete(self, db: Session, session_id: str) -> None:
        try:
            record = self.get_by_id(db, session_id)
            db.delete(record)
            db.flush()
            logger.info("PaymentSession deleted", session_id=session_id)
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to delete PaymentSession", session_id=session_id, error=str(e))
            raise DatabaseException(message="Failed to delete payment session", details=str(e))
