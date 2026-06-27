from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from config.logger import logger
from config.server_config import server_config
from repository.payment_session_repo import PaymentSessionRepo
from services.user_service import UserService
from utils.common.custom_exception import AppException, ServiceException


class PaymentSessionService:
    def __init__(self):
        self.payment_session_repo = PaymentSessionRepo()
        self.user_service = UserService()

    def initiate_session(
        self,
        db: Session,
        checkout_id: str,
        user_id: str,
        amount: int,
        currency: str,
    ):
        try:
            logger.info(
                "Initiating payment session",
                checkout_id=checkout_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
            )

            # Validate user exists — raises NotFoundException if not found
            self.user_service.get_by_id(db, user_id)

            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=server_config.payment_session_expiry_seconds
            )

            # Dummy redirect URL — replace with real provider URL when integrated
            redirect_url = f"https://pay.ledgerflow.dev/session/{checkout_id}"

            session = self.payment_session_repo.create(
                db=db,
                checkout_id=checkout_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
                redirect_url=redirect_url,
                expires_at=expires_at,
            )

            db.commit()
            logger.info(
                "Payment session initiated successfully",
                session_id=session.id,
                checkout_id=checkout_id,
                expires_at=expires_at.isoformat(),
            )
            # Return only the fields callers need — no internal state leaked
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
