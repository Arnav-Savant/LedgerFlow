from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.seller_schema import CreateSellerRequest, UpdateSellerRequest, SellerResponse
from service.seller_service import SellerService
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
from utils.common.success_response import SuccessResponse

router = APIRouter(prefix="/sellers", tags=["sellers"])


def _to_seller_response(seller) -> SellerResponse:
    return SellerResponse(
        seller_id=seller.id,
        name=seller.name,
        email=seller.email,
        is_active=seller.is_active,
        created_at=seller.created_at.isoformat() if seller.created_at else None,
        updated_at=seller.updated_at.isoformat() if seller.updated_at else None,
    )


@router.post("/", status_code=201)
def create_seller(request: CreateSellerRequest, db: Session = Depends(get_db)):
    try:
        logger.info("Create seller requested", email=request.email)
        seller = SellerService().create(db, name=request.name, email=request.email)
        data = _to_seller_response(seller)
        logger.info("Seller created", seller_id=seller.id)
        return SuccessResponse.created(data=data.model_dump(), message="Seller created successfully")
    except AppException as exc:
        logger.error("AppException in create_seller", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in create_seller", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.get("/", status_code=200)
def list_sellers(skip: int = Query(0), limit: int = Query(100), db: Session = Depends(get_db)):
    try:
        logger.info("List sellers requested", skip=skip, limit=limit)
        sellers = SellerService().get_all(db, skip=skip, limit=limit)
        data = [_to_seller_response(s).model_dump() for s in sellers]
        logger.info("Sellers listed", count=len(data))
        return SuccessResponse.ok(data=data, message="Sellers fetched successfully")
    except AppException as exc:
        logger.error("AppException in list_sellers", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in list_sellers", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.get("/{seller_id}", status_code=200)
def get_seller(seller_id: str, db: Session = Depends(get_db)):
    try:
        logger.info("Get seller requested", seller_id=seller_id)
        seller = SellerService().get_by_id(db, seller_id)
        data = _to_seller_response(seller)
        logger.info("Seller fetched", seller_id=seller_id)
        return SuccessResponse.ok(data=data.model_dump(), message="Seller fetched successfully")
    except AppException as exc:
        logger.error("AppException in get_seller", seller_id=seller_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in get_seller", seller_id=seller_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.put("/{seller_id}", status_code=200)
def update_seller(seller_id: str, request: UpdateSellerRequest, db: Session = Depends(get_db)):
    try:
        logger.info("Update seller requested", seller_id=seller_id)
        kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
        seller = SellerService().update(db, seller_id, **kwargs)
        data = _to_seller_response(seller)
        logger.info("Seller updated", seller_id=seller_id)
        return SuccessResponse.ok(data=data.model_dump(), message="Seller updated successfully")
    except AppException as exc:
        logger.error("AppException in update_seller", seller_id=seller_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in update_seller", seller_id=seller_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.delete("/{seller_id}", status_code=200)
def disable_seller(seller_id: str, db: Session = Depends(get_db)):
    try:
        logger.info("Disable seller requested", seller_id=seller_id)
        seller = SellerService().disable(db, seller_id)
        data = _to_seller_response(seller)
        logger.info("Seller disabled", seller_id=seller_id)
        return SuccessResponse.ok(data=data.model_dump(), message="Seller disabled successfully")
    except AppException as exc:
        logger.error("AppException in disable_seller", seller_id=seller_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in disable_seller", seller_id=seller_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())
