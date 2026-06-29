from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.inventory_schema import AdjustInventoryRequest, InventoryResponse
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
def list_inventory(skip: int = Query(0), limit: int = Query(100), db: Session = Depends(get_db)):
    try:
        logger.info("List inventory requested", skip=skip, limit=limit)
        items = InventoryService().get_all(db, skip=skip, limit=limit)
        data = [_to_inventory_response(i).model_dump() for i in items]
        logger.info("Inventory listed", count=len(data))
        return SuccessResponse.ok(data=data, message="Inventory fetched successfully")
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


@router.post("/product/{product_id}/adjust", status_code=200)
def adjust_inventory(product_id: str, request: AdjustInventoryRequest, db: Session = Depends(get_db)):
    try:
        logger.info("Adjust inventory requested", product_id=product_id, delta=request.delta)
        inv = InventoryService().adjust_available(db, product_id, request.delta)
        data = _to_inventory_response(inv)
        logger.info("Inventory adjusted", product_id=product_id, delta=request.delta)
        return SuccessResponse.ok(data=data.model_dump(), message="Inventory adjusted successfully")
    except AppException as exc:
        logger.error("AppException in adjust_inventory", product_id=product_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in adjust_inventory", product_id=product_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())
