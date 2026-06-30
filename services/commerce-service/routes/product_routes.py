from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.product_schema import CreateProductRequest, UpdateProductRequest, ProductResponse
from service.product_service import ProductService
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
from utils.common.success_response import SuccessResponse

router = APIRouter(prefix="/products", tags=["products"])


def _to_product_response(product) -> ProductResponse:
    return ProductResponse(
        product_id=product.id,
        seller_id=product.seller_id,
        name=product.name,
        price=product.price,
        currency=product.currency.value if hasattr(product.currency, "value") else product.currency,
        is_active=product.is_active,
        created_at=product.created_at.isoformat() if product.created_at else None,
        updated_at=product.updated_at.isoformat() if product.updated_at else None,
    )


@router.post("/", status_code=201)
def create_product(request: CreateProductRequest, db: Session = Depends(get_db)):
    try:
        logger.info("Create product requested", seller_id=request.seller_id, name=request.name)
        product = ProductService().create(
            db,
            seller_id=request.seller_id,
            name=request.name,
            price=request.price,
            currency=request.currency,
        )
        data = _to_product_response(product)
        logger.info("Product created", product_id=product.id)
        return SuccessResponse.created(data=data.model_dump(), message="Product created successfully")
    except AppException as exc:
        logger.error("AppException in create_product", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in create_product", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.get("/", status_code=200)
def list_products(skip: int = Query(0), limit: int = Query(20), db: Session = Depends(get_db)):
    try:
        logger.info("List products requested", skip=skip, limit=limit)
        svc = ProductService()
        products = svc.get_all(db, skip=skip, limit=limit)
        total = svc.count_all(db)
        data = [_to_product_response(p).model_dump() for p in products]
        logger.info("Products listed", count=len(data))
        return SuccessResponse.ok(data={"items": data, "total": total, "skip": skip, "limit": limit}, message="Products fetched successfully")
    except AppException as exc:
        logger.error("AppException in list_products", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in list_products", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.get("/{product_id}", status_code=200)
def get_product(product_id: str, db: Session = Depends(get_db)):
    try:
        logger.info("Get product requested", product_id=product_id)
        product = ProductService().get_by_id(db, product_id)
        data = _to_product_response(product)
        logger.info("Product fetched", product_id=product_id)
        return SuccessResponse.ok(data=data.model_dump(), message="Product fetched successfully")
    except AppException as exc:
        logger.error("AppException in get_product", product_id=product_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in get_product", product_id=product_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.put("/{product_id}", status_code=200)
def update_product(product_id: str, request: UpdateProductRequest, db: Session = Depends(get_db)):
    try:
        logger.info("Update product requested", product_id=product_id)
        kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
        product = ProductService().update(db, product_id, **kwargs)
        data = _to_product_response(product)
        logger.info("Product updated", product_id=product_id)
        return SuccessResponse.ok(data=data.model_dump(), message="Product updated successfully")
    except AppException as exc:
        logger.error("AppException in update_product", product_id=product_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in update_product", product_id=product_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.delete("/{product_id}", status_code=200)
def deactivate_product(product_id: str, db: Session = Depends(get_db)):
    try:
        logger.info("Deactivate product requested", product_id=product_id)
        product = ProductService().deactivate(db, product_id)
        data = _to_product_response(product)
        logger.info("Product deactivated", product_id=product_id)
        return SuccessResponse.ok(data=data.model_dump(), message="Product deactivated successfully")
    except AppException as exc:
        logger.error("AppException in deactivate_product", product_id=product_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in deactivate_product", product_id=product_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.patch("/{product_id}/reactivate", status_code=200)
def reactivate_product(product_id: str, db: Session = Depends(get_db)):
    try:
        logger.info("Reactivate product requested", product_id=product_id)
        product = ProductService().reactivate(db, product_id)
        data = _to_product_response(product)
        logger.info("Product reactivated", product_id=product_id)
        return SuccessResponse.ok(data=data.model_dump(), message="Product reactivated successfully")
    except AppException as exc:
        logger.error("AppException in reactivate_product", product_id=product_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in reactivate_product", product_id=product_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())
