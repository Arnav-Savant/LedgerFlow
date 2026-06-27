from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from config.database import get_db
from config.logger import logger
from services.payment_session_service import PaymentSessionService
from schema.payment_session_schema import (
    PaymentSessionInitiateRequest,
    PaymentSessionInitiateResponse,
)
from utils.common.custom_exception import AppException
from utils.common.success_response import SuccessResponse
from utils.common.error_response import ErrorResponse

router = APIRouter(prefix="/payment-sessions", tags=["Payment Sessions"])


@router.post("/initiate")
def initiate_payment_session(
    request: PaymentSessionInitiateRequest,
    db: Session = Depends(get_db),
):
    try:
        logger.info(
            "Received payment session initiation request",
            checkout_id=request.checkout_id,
            user_id=request.user_id,
        )
        payment_session_service = PaymentSessionService()
        result = payment_session_service.initiate_session(
            db=db,
            checkout_id=request.checkout_id,
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency,
        )
        data = PaymentSessionInitiateResponse(
            session_id=result["session_id"],
            redirect_url=result["redirect_url"],
        )
        logger.info("Payment session initiation response sent", session_id=result["session_id"])
        return SuccessResponse.created(
            data=data.model_dump(),
            message="Payment session initiated successfully",
        )
    except AppException as exc:
        logger.warning(
            "Payment session initiation failed",
            error=exc.error,
            message=exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.from_exception(exc).model_dump(),
        )
    except Exception as exc:
        logger.exception("Unexpected error in initiate_payment_session", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=ErrorResponse.internal_error().model_dump(),
        )
