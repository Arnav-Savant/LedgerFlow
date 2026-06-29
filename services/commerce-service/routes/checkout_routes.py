from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.checkout_schema import (
    CheckoutInitiateRequest,
    CheckoutInitiateResponse,
    CheckoutDetailResponse,
    CheckoutListItemResponse,
    OrderSummary,
)
from service.checkout_service import CheckoutService
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
from utils.common.success_response import SuccessResponse

router = APIRouter(prefix="/checkouts", tags=["checkouts"])

# ── Middleware note ────────────────────────────────────────────────────────────
# POST /checkouts/initiate is guarded by UserValidationMiddleware (registered in
# main.py).  Before this handler executes, the middleware reads the request body,
# extracts user_id, and queries the user repository.  If the user does not exist
# the middleware short-circuits with a 404 ErrorResponse and this handler never
# runs.  No explicit user validation is therefore needed inside this route.
# ──────────────────────────────────────────────────────────────────────────────


def _build_order_summary(order) -> OrderSummary:
    return OrderSummary(
        order_id=order.id,
        product_id=order.product_id,
        seller_id=order.seller_id,
        amount=order.amount,
        currency=order.currency.value if hasattr(order.currency, "value") else order.currency,
        order_status=order.order_status.value if hasattr(order.order_status, "value") else order.order_status,
    )


@router.post("/initiate", status_code=201)
def initiate_checkout(
    request: CheckoutInitiateRequest,
    db: Session = Depends(get_db),
):
    checkout_service = CheckoutService()
    try:
        logger.info("Initiate checkout requested", user_id=request.user_id)
        products = [{"product_id": p.product_id, "quantity": p.quantity} for p in request.products]
        result = checkout_service.initiate_checkout(db, request.user_id, products)

        checkout = result["checkout"]
        orders = result["orders"]

        data = CheckoutInitiateResponse(
            checkout_id=checkout.id,
            user_id=checkout.user_id,
            checkout_status=checkout.status.value if hasattr(checkout.status, "value") else checkout.status,
            total_amount=checkout.total_amount,
            payment_session_id=result["payment_session_id"],
            redirect_url=result["redirect_url"],
            order_ids=[o.id for o in orders],
            orders=[_build_order_summary(o) for o in orders],
        )
        return SuccessResponse.created(data=data.model_dump(), message="Checkout initiated successfully")

    except AppException as exc:
        logger.error(
            "AppException in initiate_checkout",
            error=exc.error,
            detail=exc.message,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.from_exception(exc).model_dump(),
        )
    except Exception as exc:
        logger.exception("Unhandled error in initiate_checkout", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=ErrorResponse.internal_error().model_dump(),
        )


@router.get("/", status_code=200)
def list_checkouts(skip: int = Query(0), limit: int = Query(100), db: Session = Depends(get_db)):
    try:
        logger.info("Checkout list requested", skip=skip, limit=limit)
        checkouts = CheckoutService().get_all_checkouts(db, skip=skip, limit=limit)
        data = [
            CheckoutListItemResponse(
                checkout_id=c.id,
                user_id=c.user_id,
                checkout_status=c.status.value if hasattr(c.status, "value") else c.status,
                total_amount=c.total_amount,
                payment_session_id=c.payment_session_id,
                created_at=c.created_at.isoformat() if c.created_at else None,
                updated_at=c.updated_at.isoformat() if c.updated_at else None,
            ).model_dump()
            for c in checkouts
        ]
        logger.info("Checkout list returned", count=len(data))
        return SuccessResponse.ok(data=data, message="Checkouts fetched successfully")
    except AppException as exc:
        logger.error("AppException in list_checkouts", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in list_checkouts", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.get("/{checkout_id}", status_code=200)
def get_checkout(checkout_id: str, db: Session = Depends(get_db)):
    checkout_service = CheckoutService()
    try:
        logger.info("Get checkout requested", checkout_id=checkout_id)
        checkout, orders = checkout_service.get_checkout(db, checkout_id)

        data = CheckoutDetailResponse(
            checkout_id=checkout.id,
            user_id=checkout.user_id,
            checkout_status=checkout.status.value if hasattr(checkout.status, "value") else checkout.status,
            total_amount=checkout.total_amount,
            payment_session_id=checkout.payment_session_id,
            created_at=checkout.created_at.isoformat() if checkout.created_at else None,
            updated_at=checkout.updated_at.isoformat() if checkout.updated_at else None,
            orders=[_build_order_summary(o) for o in orders],
        )
        return SuccessResponse.ok(data=data.model_dump(), message="Checkout fetched successfully")

    except AppException as exc:
        logger.error(
            "AppException in get_checkout",
            checkout_id=checkout_id,
            error=exc.error,
            detail=exc.message,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.from_exception(exc).model_dump(),
        )
    except Exception as exc:
        logger.exception("Unhandled error in get_checkout", checkout_id=checkout_id, error=str(exc))
        return JSONResponse(
            status_code=500,
            content=ErrorResponse.internal_error().model_dump(),
        )
