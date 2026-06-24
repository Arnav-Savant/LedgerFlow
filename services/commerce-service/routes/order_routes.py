from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.order_schema import OrderDetailResponse, ProductDetail
from service.order_service import OrderService
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
from utils.common.success_response import SuccessResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}", status_code=200)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order_service = OrderService()
    try:
        order, product = order_service.get_by_id(db, order_id)

        data = OrderDetailResponse(
            order_id=order.id,
            checkout_id=order.checkout_id,
            user_id=order.user_id,
            seller_id=order.seller_id,
            amount=order.amount,
            currency=order.currency.value if hasattr(order.currency, "value") else order.currency,
            order_status=order.order_status.value if hasattr(order.order_status, "value") else order.order_status,
            checkout_status=order.checkout_status.value if hasattr(order.checkout_status, "value") else order.checkout_status,
            product=ProductDetail(
                product_id=product.id,
                name=product.name,
                price=product.price,
                currency=product.currency.value if hasattr(product.currency, "value") else product.currency,
            ),
            ledger_updated=order.ledger_updated,
            wallet_updated=order.wallet_updated,
        )
        return SuccessResponse.ok(data=data.model_dump(), message="Order fetched successfully")

    except AppException as exc:
        logger.error(
            "AppException in get_order",
            order_id=order_id,
            error=exc.error,
            message=exc.message,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.from_exception(exc).model_dump(),
        )
    except Exception as exc:
        logger.exception("Unhandled error in get_order", order_id=order_id, error=str(exc))
        return JSONResponse(
            status_code=500,
            content=ErrorResponse.internal_error().model_dump(),
        )
