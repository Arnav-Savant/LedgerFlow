from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from config.logger import logger
from config.server_config import server_config
from models.payment_session import PaymentSession
from repository.payment_session_repo import PaymentSessionRepo
from repository.payment_attempt_repo import PaymentAttemptRepo
from services.user_service import UserService
from utils.common.custom_exception import AppException, ServiceException
from utils.enums import PaymentStatus


_TERMINAL_STATUSES = {
    PaymentStatus.SUCCESS,
    PaymentStatus.FAILED,
    PaymentStatus.EXPIRED,
    PaymentStatus.CANCELLED,
}


def _compute_ui_state(session: PaymentSession, is_expired: bool) -> str:
    if is_expired or session.status == PaymentStatus.EXPIRED:
        return "EXPIRED"
    if session.status == PaymentStatus.SUCCESS:
        return "SUCCESS"
    if session.status in {PaymentStatus.FAILED, PaymentStatus.CANCELLED}:
        return "FAILED"
    if session.attempt_count == 0:
        return "PAYMENT_PAGE"
    return "RETRY"


class PaymentSessionService:
    def __init__(self):
        self.payment_session_repo = PaymentSessionRepo()
        self.payment_attempt_repo = PaymentAttemptRepo()
        self.user_service = UserService()

    # ── Top-level operations (own their transaction) ──────────────────────────

    def initiate_session(
        self,
        db: Session,
        checkout_id: str,
        user_id: str,
        amount: int,
        currency: str,
    ) -> dict:
        try:
            logger.info(
                "Initiating payment session",
                checkout_id=checkout_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
            )

            self.user_service.get_by_id(db, user_id)

            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=server_config.payment_session_expiry_seconds
            )

            session = self.payment_session_repo.create(
                db=db,
                checkout_id=checkout_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
                redirect_url="",  # filled after flush gives us the real ID
                expires_at=expires_at,
                max_attempts=server_config.payment_session_max_attempts,
            )

            session.redirect_url = f"{server_config.payment_frontend_base_url}/{session.id}"
            db.flush()

            db.commit()
            logger.info(
                "Payment session initiated successfully",
                session_id=session.id,
                checkout_id=checkout_id,
                expires_at=expires_at.isoformat(),
            )
            return {"session_id": session.id, "redirect_url": session.redirect_url}

        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            logger.error(
                "Unexpected error initiating payment session",
                checkout_id=checkout_id,
                user_id=user_id,
                error=str(exc),
            )
            raise ServiceException(
                message="Failed to initiate payment session",
                details=str(exc),
            )

    def get_session(self, db: Session, session_id: str) -> dict:
        try:
            logger.info("Fetching payment session detail", session_id=session_id)

            session = self.payment_session_repo.get_by_id(db, session_id)

            now = datetime.now(timezone.utc)
            expires_at = session.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            is_expired = now > expires_at

            if is_expired and session.status not in _TERMINAL_STATUSES:
                session = self.payment_session_repo.update_status(
                    db, session_id, PaymentStatus.EXPIRED
                )
                db.commit()
                logger.info("Payment session marked as EXPIRED on read", session_id=session_id)

            attempts = self.payment_attempt_repo.get_all_by_session_id(db, session_id)

            ui_state = _compute_ui_state(session, is_expired)
            can_retry = (
                not is_expired
                and session.status == PaymentStatus.INITIATED
                and session.attempt_count < session.max_attempts
            )

            logger.info(
                "Payment session detail fetched",
                session_id=session_id,
                status=session.status,
                ui_state=ui_state,
                attempt_count=session.attempt_count,
            )

            return {
                "session_id": session.id,
                "status": session.status,
                "amount": session.amount,
                "currency": session.currency,
                "payment_method": session.payment_method,
                "attempt_count": session.attempt_count,
                "max_attempts": session.max_attempts,
                "expires_at": expires_at.isoformat(),
                "ui_state": ui_state,
                "can_retry": can_retry,
                "attempts": [
                    {
                        "attempt_id": a.id,
                        "status": a.status,
                        "failure_reason": a.failure_reason,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in attempts
                ],
            }

        except AppException:
            raise
        except Exception as exc:
            logger.error(
                "Unexpected error fetching payment session",
                session_id=session_id,
                error=str(exc),
            )
            raise ServiceException(
                message="Failed to fetch payment session",
                details=str(exc),
            )

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> list:
        try:
            from datetime import datetime, timezone
            logger.info("Fetching all payment sessions", skip=skip, limit=limit)
            sessions = self.payment_session_repo.get_all(db, skip=skip, limit=limit)
            now = datetime.now(timezone.utc)
            result = []
            for session in sessions:
                expires_at = session.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                is_expired = now > expires_at
                ui_state = _compute_ui_state(session, is_expired)
                can_retry = (
                    not is_expired
                    and session.status == PaymentStatus.INITIATED
                    and session.attempt_count < session.max_attempts
                )
                result.append({
                    "session_id": session.id,
                    "checkout_id": session.checkout_id,
                    "user_id": session.user_id,
                    "status": session.status.value if hasattr(session.status, "value") else session.status,
                    "amount": session.amount,
                    "currency": session.currency.value if hasattr(session.currency, "value") else session.currency,
                    "attempt_count": session.attempt_count,
                    "max_attempts": session.max_attempts,
                    "expires_at": expires_at.isoformat(),
                    "ui_state": ui_state,
                    "can_retry": can_retry,
                    "redirect_url": session.redirect_url,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                })
            logger.info("Payment sessions fetched", count=len(result))
            return result
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error listing payment sessions", error=str(exc))
            raise ServiceException(message="Failed to list payment sessions", details=str(exc))

    # ── Internal helpers called by PaymentAttemptService ─────────────────────
    # These flush only — the caller (PaymentAttemptService) owns the commit.

    def get_by_id(self, db: Session, session_id: str) -> PaymentSession:
        """Return the raw PaymentSession ORM object for use by sibling services."""
        try:
            return self.payment_session_repo.get_by_id(db, session_id)
        except AppException:
            raise
        except Exception as exc:
            logger.error("Unexpected error fetching session by id", session_id=session_id, error=str(exc))
            raise ServiceException(message="Failed to fetch payment session", details=str(exc))

    def mark_expired(self, db: Session, session_id: str) -> PaymentSession:
        """Mark session EXPIRED and flush. Caller commits."""
        try:
            session = self.payment_session_repo.update_status(db, session_id, PaymentStatus.EXPIRED)
            logger.info("Payment session marked EXPIRED", session_id=session_id)
            return session
        except AppException:
            raise
        except Exception as exc:
            logger.error("Unexpected error marking session EXPIRED", session_id=session_id, error=str(exc))
            raise ServiceException(message="Failed to mark session as expired", details=str(exc))

    def mark_success(self, db: Session, session_id: str) -> PaymentSession:
        """Mark session SUCCESS and flush. Caller commits."""
        try:
            session = self.payment_session_repo.update_status(db, session_id, PaymentStatus.SUCCESS)
            logger.info("Payment session marked SUCCESS", session_id=session_id)
            return session
        except AppException:
            raise
        except Exception as exc:
            logger.error("Unexpected error marking session SUCCESS", session_id=session_id, error=str(exc))
            raise ServiceException(message="Failed to mark session as success", details=str(exc))

    def mark_failed(self, db: Session, session_id: str) -> PaymentSession:
        """Mark session FAILED and flush. Caller commits."""
        try:
            session = self.payment_session_repo.update_status(db, session_id, PaymentStatus.FAILED)
            logger.info("Payment session marked FAILED", session_id=session_id)
            return session
        except AppException:
            raise
        except Exception as exc:
            logger.error("Unexpected error marking session FAILED", session_id=session_id, error=str(exc))
            raise ServiceException(message="Failed to mark session as failed", details=str(exc))

    def increment_attempt_count(self, db: Session, session_id: str) -> PaymentSession:
        """Increment session attempt_count and flush. Caller commits."""
        try:
            session = self.payment_session_repo.increment_attempt_count(db, session_id)
            logger.info(
                "Session attempt_count incremented via service",
                session_id=session_id,
                attempt_count=session.attempt_count,
            )
            return session
        except AppException:
            raise
        except Exception as exc:
            logger.error("Unexpected error incrementing attempt count", session_id=session_id, error=str(exc))
            raise ServiceException(message="Failed to increment attempt count", details=str(exc))
