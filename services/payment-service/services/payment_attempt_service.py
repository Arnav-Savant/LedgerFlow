import random
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from config.logger import logger
from config.server_config import server_config
from repository.payment_attempt_repo import PaymentAttemptRepo
from services.payment_session_service import PaymentSessionService
from utils.common.custom_exception import AppException, ServiceException, ValidationException
from utils.enums import AttemptStatus, PaymentMethod, PaymentStatus


_TERMINAL_STATUSES = {
    PaymentStatus.SUCCESS,
    PaymentStatus.FAILED,
    PaymentStatus.EXPIRED,
    PaymentStatus.CANCELLED,
}


def _simulate_psp() -> bool:
    """Returns True (success) or False (failure) based on config or random."""
    if server_config.psp_simulate_success is True:
        return True
    if server_config.psp_simulate_success is False:
        return False
    return random.choice([True, False])


class PaymentAttemptService:
    def __init__(self):
        self.attempt_repo = PaymentAttemptRepo()
        self.session_service = PaymentSessionService()

    def create_attempt(
        self,
        db: Session,
        session_id: str,
        idempotency_key: str,
        payment_method: PaymentMethod,
    ) -> dict:
        try:
            logger.info(
                "Creating payment attempt",
                session_id=session_id,
                idempotency_key=idempotency_key,
                payment_method=payment_method,
            )

            # ── 1. Fetch session via session service ──────────────────────────
            session = self.session_service.get_by_id(db, session_id)

            # ── 2. Expiry check ───────────────────────────────────────────────
            now = datetime.now(timezone.utc)
            expires_at = session.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if now > expires_at and session.status not in _TERMINAL_STATUSES:
                self.session_service.mark_expired(db, session_id)
                db.commit()
                logger.warning("Payment session expired during attempt creation", session_id=session_id)
                raise ValidationException(
                    message="Payment session has expired",
                    details={"session_id": session_id},
                )

            # ── 3. Terminal status guard ──────────────────────────────────────
            if session.status in _TERMINAL_STATUSES:
                logger.warning(
                    "Attempt blocked — session is in terminal state",
                    session_id=session_id,
                    status=session.status,
                )
                raise ValidationException(
                    message=f"Payment session is {session.status} and cannot accept new attempts",
                    details={"session_id": session_id, "status": session.status},
                )

            # ── 4. Max attempts guard ─────────────────────────────────────────
            if session.attempt_count >= session.max_attempts:
                logger.warning(
                    "Attempt blocked — max attempts reached",
                    session_id=session_id,
                    attempt_count=session.attempt_count,
                    max_attempts=session.max_attempts,
                )
                raise ValidationException(
                    message="Maximum payment attempts reached for this session",
                    details={
                        "session_id": session_id,
                        "attempt_count": session.attempt_count,
                        "max_attempts": session.max_attempts,
                    },
                )

            # ── 5. Idempotency check ──────────────────────────────────────────
            existing = self.attempt_repo.get_by_idempotency_key(db, session_id, idempotency_key)
            if existing is not None:
                logger.info(
                    "Idempotent attempt — returning existing",
                    attempt_id=existing.id,
                    session_id=session_id,
                    idempotency_key=idempotency_key,
                )
                return {
                    "attempt_id": existing.id,
                    "status": existing.status,
                    "failure_reason": existing.failure_reason,
                    "session_status": session.status,
                }

            # ── 6. Create attempt (PENDING) ───────────────────────────────────
            attempt = self.attempt_repo.create(
                db=db,
                session_id=session_id,
                idempotency_key=idempotency_key,
                payment_method=payment_method,
            )

            # ── 7. Increment session attempt_count via session service ─────────
            session = self.session_service.increment_attempt_count(db, session_id)

            # ── 8. Simulate PSP ───────────────────────────────────────────────
            psp_success = _simulate_psp()
            logger.info(
                "PSP simulation result",
                attempt_id=attempt.id,
                session_id=session_id,
                success=psp_success,
            )

            # ── 9 & 10. Update attempt + session based on PSP outcome ─────────
            if psp_success:
                psp_reference = f"PSP-{uuid.uuid4().hex[:12].upper()}"
                self.attempt_repo.update_status(
                    db, attempt.id, AttemptStatus.SUCCESS, psp_reference=psp_reference,
                )
                self.session_service.mark_success(db, session_id)
                final_attempt_status = AttemptStatus.SUCCESS
                final_session_status = PaymentStatus.SUCCESS
                failure_reason = None
                logger.info(
                    "Payment attempt succeeded",
                    attempt_id=attempt.id,
                    session_id=session_id,
                    psp_reference=psp_reference,
                )
            else:
                failure_reason = "Payment declined by payment processor"
                self.attempt_repo.update_status(
                    db, attempt.id, AttemptStatus.FAILED, failure_reason=failure_reason,
                )
                if session.attempt_count >= session.max_attempts:
                    self.session_service.mark_failed(db, session_id)
                    final_session_status = PaymentStatus.FAILED
                    logger.warning(
                        "Payment attempt failed — max attempts reached, session marked FAILED",
                        attempt_id=attempt.id,
                        session_id=session_id,
                    )
                else:
                    final_session_status = session.status  # stays INITIATED, retries available
                    logger.warning(
                        "Payment attempt failed — retries available",
                        attempt_id=attempt.id,
                        session_id=session_id,
                        remaining=session.max_attempts - session.attempt_count,
                    )
                final_attempt_status = AttemptStatus.FAILED

            # ── 11. Single commit for the entire attempt lifecycle ─────────────
            db.commit()
            logger.info(
                "Payment attempt committed",
                attempt_id=attempt.id,
                session_id=session_id,
                attempt_status=final_attempt_status,
                session_status=final_session_status,
            )

            return {
                "attempt_id": attempt.id,
                "status": final_attempt_status,
                "failure_reason": failure_reason,
                "session_status": final_session_status,
            }

        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            logger.error(
                "Unexpected error creating payment attempt",
                session_id=session_id,
                idempotency_key=idempotency_key,
                error=str(exc),
            )
            raise ServiceException(
                message="Failed to create payment attempt",
                details=str(exc),
            )
