import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.payment_attempt import PaymentAttempt
from config.logger import logger
from utils.common.custom_exception import DatabaseException, NotFoundException
from utils.enums import AttemptStatus, PaymentMethod


class PaymentAttemptRepo:
    def create(
        self,
        db: Session,
        session_id: str,
        idempotency_key: str,
        payment_method: PaymentMethod,
    ) -> PaymentAttempt:
        try:
            attempt = PaymentAttempt(
                id=str(uuid.uuid4()),
                session_id=session_id,
                idempotency_key=idempotency_key,
                payment_method=payment_method,
                status=AttemptStatus.PENDING,
            )
            db.add(attempt)
            db.flush()
            db.refresh(attempt)
            logger.info(
                "PaymentAttempt created",
                attempt_id=attempt.id,
                session_id=session_id,
                idempotency_key=idempotency_key,
                payment_method=payment_method,
            )
            return attempt
        except SQLAlchemyError as e:
            logger.error(
                "Failed to create PaymentAttempt",
                session_id=session_id,
                idempotency_key=idempotency_key,
                error=str(e),
            )
            raise DatabaseException(message="Failed to create payment attempt", details=str(e))

    def get_by_id(self, db: Session, attempt_id: str) -> PaymentAttempt:
        try:
            logger.debug("Fetching PaymentAttempt by id", attempt_id=attempt_id)
            record = db.query(PaymentAttempt).filter(PaymentAttempt.id == attempt_id).first()
            if record is None:
                logger.warning("PaymentAttempt not found", attempt_id=attempt_id)
                raise NotFoundException("PaymentAttempt", attempt_id)
            return record
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error("Failed to fetch PaymentAttempt by id", attempt_id=attempt_id, error=str(e))
            raise DatabaseException(message="Failed to fetch payment attempt", details=str(e))

    def get_by_idempotency_key(
        self,
        db: Session,
        session_id: str,
        idempotency_key: str,
    ) -> Optional[PaymentAttempt]:
        try:
            logger.debug(
                "Checking idempotency key",
                session_id=session_id,
                idempotency_key=idempotency_key,
            )
            return (
                db.query(PaymentAttempt)
                .filter(
                    PaymentAttempt.session_id == session_id,
                    PaymentAttempt.idempotency_key == idempotency_key,
                )
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(
                "Failed to fetch PaymentAttempt by idempotency key",
                session_id=session_id,
                idempotency_key=idempotency_key,
                error=str(e),
            )
            raise DatabaseException(
                message="Failed to fetch payment attempt by idempotency key", details=str(e)
            )

    def get_all_by_session_id(self, db: Session, session_id: str) -> list[PaymentAttempt]:
        try:
            records = (
                db.query(PaymentAttempt)
                .filter(PaymentAttempt.session_id == session_id)
                .order_by(PaymentAttempt.created_at.asc())
                .all()
            )
            logger.debug("Fetched PaymentAttempts for session", session_id=session_id, count=len(records))
            return records
        except SQLAlchemyError as e:
            logger.error("Failed to fetch PaymentAttempts by session_id", session_id=session_id, error=str(e))
            raise DatabaseException(
                message="Failed to fetch payment attempts for session", details=str(e)
            )

    def update_status(
        self,
        db: Session,
        attempt_id: str,
        status: AttemptStatus,
        psp_reference: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> PaymentAttempt:
        try:
            record = self.get_by_id(db, attempt_id)
            old_status = record.status
            record.status = status
            if psp_reference is not None:
                record.psp_reference = psp_reference
            if failure_reason is not None:
                record.failure_reason = failure_reason
            db.flush()
            db.refresh(record)
            logger.info(
                "PaymentAttempt status updated",
                attempt_id=attempt_id,
                old_status=old_status,
                new_status=status,
                psp_reference=psp_reference,
            )
            return record
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Failed to update PaymentAttempt status",
                attempt_id=attempt_id,
                status=status,
                error=str(e),
            )
            raise DatabaseException(message="Failed to update payment attempt status", details=str(e))
