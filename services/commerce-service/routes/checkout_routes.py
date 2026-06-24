from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.checkout_schema import (
    CheckoutInitiateRequest,
    CheckoutInitiateResponse,
    CheckoutDetailResponse,
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
        products = [{"product_id": p.product_id, "quantity": p.quantity} for p in request.products]
        result = checkout_service.initiate_checkout(db, request.user_id, products)

        checkout = result["checkout"]
        orders = result["orders"]

        data = CheckoutInitiateResponse(
            checkout_id=checkout.id,
            user_id=checkout.user_id,
            checkout_status=checkout.status.value if hasattr(checkout.status, "value") else checkout.status,
            total_amount=checkout.total_amount,
            order_ids=[o.id for o in orders],
            orders=[_build_order_summary(o) for o in orders],
        )
        return SuccessResponse.created(data=data.model_dump(), message="Checkout initiated successfully")

    except AppException as exc:
        logger.error(
            "AppException in initiate_checkout",
            error=exc.error,
            message=exc.message,
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


@router.get("/{checkout_id}", status_code=200)
def get_checkout(checkout_id: str, db: Session = Depends(get_db)):
    checkout_service = CheckoutService()
    try:
        checkout, orders = checkout_service.get_checkout(db, checkout_id)

        data = CheckoutDetailResponse(
            checkout_id=checkout.id,
            user_id=checkout.user_id,
            checkout_status=checkout.status.value if hasattr(checkout.status, "value") else checkout.status,
            total_amount=checkout.total_amount,
            orders=[_build_order_summary(o) for o in orders],
        )
        return SuccessResponse.ok(data=data.model_dump(), message="Checkout fetched successfully")

    except AppException as exc:
        logger.error(
            "AppException in get_checkout",
            checkout_id=checkout_id,
            error=exc.error,
            message=exc.message,
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
