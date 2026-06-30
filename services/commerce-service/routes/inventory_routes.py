from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.inventory_schema import StockUpdateRequest, InventoryResponse
from service.inventory_service import InventoryService
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
from utils.common.success_response import SuccessResponse

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _to_inventory_response(inv) -> InventoryResponse:
    return InventoryResponse(
        inventory_id=inv.id,
        product_id=inv.product_id,
        available_quantity=inv.available_quantity,
        reserved_quantity=inv.reserved_quantity,
        updated_at=inv.updated_at.isoformat() if inv.updated_at else None,
    )


@router.get("/", status_code=200)
def list_inventory(skip: int = Query(0), limit: int = Query(20), db: Session = Depends(get_db)):
    try:
        logger.info("List inventory requested", skip=skip, limit=limit)
        svc = InventoryService()
        items = svc.get_all(db, skip=skip, limit=limit)
        total = svc.count_all(db)
        data = [_to_inventory_response(i).model_dump() for i in items]
        logger.info("Inventory listed", count=len(data))
        return SuccessResponse.ok(data={"items": data, "total": total, "skip": skip, "limit": limit}, message="Inventory fetched successfully")
    except AppException as exc:
        logger.error("AppException in list_inventory", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in list_inventory", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.get("/product/{product_id}", status_code=200)
def get_inventory_by_product(product_id: str, db: Session = Depends(get_db)):
    try:
        logger.info("Get inventory by product requested", product_id=product_id)
        inv = InventoryService().get_by_product_id(db, product_id)
        data = _to_inventory_response(inv)
        logger.info("Inventory fetched by product", product_id=product_id)
        return SuccessResponse.ok(data=data.model_dump(), message="Inventory fetched successfully")
    except AppException as exc:
        logger.error("AppException in get_inventory_by_product", product_id=product_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in get_inventory_by_product", product_id=product_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.post("/product/{product_id}/stock", status_code=200)
def update_stock(product_id: str, request: StockUpdateRequest, db: Session = Depends(get_db)):
    try:
        if request.operation not in ("add", "remove"):
            from fastapi.responses import JSONResponse as _JSONResponse
            return _JSONResponse(status_code=400, content={"error": "operation must be add or remove"})
        svc = InventoryService()
        if request.operation == "add":
            inv = svc.add_stock(db, product_id, request.quantity)
        else:
            inv = svc.remove_stock(db, product_id, request.quantity)
        data = _to_inventory_response(inv)
        return SuccessResponse.ok(data=data.model_dump(), message=f"Stock {request.operation}ed successfully")
    except AppException as exc:
        logger.error("AppException in update_stock", product_id=product_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in update_stock", product_id=product_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())
