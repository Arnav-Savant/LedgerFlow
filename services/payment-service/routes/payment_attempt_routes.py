from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from config.database import get_db
from config.logger import logger
from services.payment_attempt_service import PaymentAttemptService
from schema.payment_attempt_schema import PaymentAttemptRequest, PaymentAttemptResponse
from utils.common.custom_exception import AppException
from utils.common.success_response import SuccessResponse
from utils.common.error_response import ErrorResponse

router = APIRouter(prefix="/payment-sessions", tags=["Payment Attempts"])


@router.post("/{session_id}/attempt")
def create_payment_attempt(
    session_id: str,
    request: PaymentAttemptRequest,
    db: Session = Depends(get_db),
):
    try:
        logger.info(
            "Received payment attempt request",
            session_id=session_id,
            idempotency_key=request.idempotency_key,
            payment_method=request.payment_method,
        )
        result = PaymentAttemptService().create_attempt(
            db=db,
            session_id=session_id,
            idempotency_key=request.idempotency_key,
            payment_method=request.payment_method,
        )
        data = PaymentAttemptResponse(
            attempt_id=result["attempt_id"],
            status=result["status"],
            failure_reason=result["failure_reason"],
            session_status=result["session_status"],
        )
        logger.info(
            "Payment attempt response sent",
            attempt_id=result["attempt_id"],
            status=result["status"],
            session_status=result["session_status"],
        )
        return SuccessResponse.created(
            data=data.model_dump(),
            message="Payment attempt processed",
        )
    except AppException as exc:
        logger.error(
            "Payment attempt failed",
            session_id=session_id,
            error=exc.error,
            detail=exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.from_exception(exc).model_dump(),
        )
    except Exception as exc:
        logger.exception(
            "Unexpected error in create_payment_attempt",
            session_id=session_id,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse.internal_error().model_dump(),
        )
