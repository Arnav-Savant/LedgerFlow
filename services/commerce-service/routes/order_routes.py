from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.order_schema import OrderDetailResponse, ProductDetail, OrderListItemResponse
from service.order_service import OrderService
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
from utils.common.success_response import SuccessResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", status_code=200)
def list_orders(skip: int = Query(0), limit: int = Query(20), db: Session = Depends(get_db)):
    try:
        logger.info("Order list requested", skip=skip, limit=limit)
        svc = OrderService()
        orders = svc.get_all(db, skip=skip, limit=limit)
        total = svc.count_all(db)
        data = [OrderListItemResponse(**o).model_dump() for o in orders]
        logger.info("Order list returned", count=len(data))
        return SuccessResponse.ok(data={"items": data, "total": total, "skip": skip, "limit": limit}, message="Orders fetched successfully")
    except AppException as exc:
        logger.error("AppException in list_orders", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in list_orders", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.get("/{order_id}", status_code=200)
def get_order(order_id: str, db: Session = Depends(get_db)):
    try:
        logger.info("Order detail requested", order_id=order_id)
        order, product, seller_name = OrderService().get_by_id(db, order_id)
        data = OrderDetailResponse(
            order_id=order.id,
            checkout_id=order.checkout_id,
            user_id=order.user_id,
            seller_id=order.seller_id,
            seller_name=seller_name,
            quantity=order.quantity,
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
        logger.info("Order detail returned", order_id=order_id)
        return SuccessResponse.ok(data=data.model_dump(), message="Order fetched successfully")
    except AppException as exc:
        logger.error("AppException in get_order", order_id=order_id, error=exc.error, detail=exc.message, status_code=exc.status_code)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in get_order", order_id=order_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())
