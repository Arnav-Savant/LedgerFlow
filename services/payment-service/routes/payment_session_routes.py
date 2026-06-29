from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from config.database import get_db
from config.logger import logger
from services.payment_session_service import PaymentSessionService
from schema.payment_session_schema import (
    PaymentSessionInitiateRequest,
    PaymentSessionInitiateResponse,
    PaymentSessionDetailResponse,
    PaymentSessionListItemResponse,
    AttemptSummary,
)
from utils.common.custom_exception import AppException
from utils.common.success_response import SuccessResponse
from utils.common.error_response import ErrorResponse

router = APIRouter(prefix="/payment-sessions", tags=["Payment Sessions"])


@router.get("/")
def list_payment_sessions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    try:
        logger.info("Payment sessions list requested", skip=skip, limit=limit)
        result = PaymentSessionService().list_all(db=db, skip=skip, limit=limit)
        data = [PaymentSessionListItemResponse(**s).model_dump() for s in result]
        logger.info("Payment sessions list returned", count=len(data))
        return SuccessResponse.ok(data=data, message="Payment sessions fetched successfully")
    except AppException as exc:
        logger.error("AppException in list_payment_sessions", error=exc.error, detail=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.from_exception(exc).model_dump(),
        )
    except Exception as exc:
        logger.exception("Unexpected error in list_payment_sessions", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=ErrorResponse.internal_error().model_dump(),
        )


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
        result = PaymentSessionService().initiate_session(
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
        logger.error(
            "Payment session initiation failed",
            error=exc.error,
            detail=exc.message,
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


@router.get("/{session_id}")
def get_payment_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    try:
        logger.info("Received payment session detail request", session_id=session_id)
        result = PaymentSessionService().get_session(db=db, session_id=session_id)
        data = PaymentSessionDetailResponse(
            session_id=result["session_id"],
            status=result["status"],
            amount=result["amount"],
            currency=result["currency"],
            payment_method=result["payment_method"],
            attempt_count=result["attempt_count"],
            max_attempts=result["max_attempts"],
            expires_at=result["expires_at"],
            ui_state=result["ui_state"],
            can_retry=result["can_retry"],
            attempts=[AttemptSummary(**a) for a in result["attempts"]],
        )
        logger.info(
            "Payment session detail response sent",
            session_id=session_id,
            ui_state=result["ui_state"],
        )
        return SuccessResponse.ok(
            data=data.model_dump(),
            message="Payment session fetched successfully",
        )
    except AppException as exc:
        logger.error(
            "Payment session fetch failed",
            session_id=session_id,
            error=exc.error,
            detail=exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.from_exception(exc).model_dump(),
        )
    except Exception as exc:
        logger.exception("Unexpected error in get_payment_session", session_id=session_id, error=str(exc))
        return JSONResponse(
            status_code=500,
            content=ErrorResponse.internal_error().model_dump(),
        )
