from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.user_schema import CreateUserRequest, UpdateUserRequest, UserResponse
from service.user_service import UserService
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
from utils.common.success_response import SuccessResponse

router = APIRouter(prefix="/users", tags=["users"])


def _to_user_response(user) -> UserResponse:
    return UserResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.post("/", status_code=201)
def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    try:
        logger.info("Create user requested", email=request.email)
        user = UserService().create(db, name=request.name, email=request.email, phone=request.phone)
        data = _to_user_response(user)
        logger.info("User created", user_id=user.id)
        return SuccessResponse.created(data=data.model_dump(), message="User created successfully")
    except AppException as exc:
        logger.error("AppException in create_user", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in create_user", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.get("/", status_code=200)
def list_users(skip: int = Query(0), limit: int = Query(20), db: Session = Depends(get_db)):
    try:
        logger.info("List users requested", skip=skip, limit=limit)
        svc = UserService()
        users = svc.get_all(db, skip=skip, limit=limit)
        total = svc.count_all(db)
        data = [_to_user_response(u).model_dump() for u in users]
        logger.info("Users listed", count=len(data))
        return SuccessResponse.ok(data={"items": data, "total": total, "skip": skip, "limit": limit}, message="Users fetched successfully")
    except AppException as exc:
        logger.error("AppException in list_users", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in list_users", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.get("/{user_id}", status_code=200)
def get_user(user_id: str, db: Session = Depends(get_db)):
    try:
        logger.info("Get user requested", user_id=user_id)
        user = UserService().get_by_id(db, user_id)
        data = _to_user_response(user)
        logger.info("User fetched", user_id=user_id)
        return SuccessResponse.ok(data=data.model_dump(), message="User fetched successfully")
    except AppException as exc:
        logger.error("AppException in get_user", user_id=user_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in get_user", user_id=user_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.put("/{user_id}", status_code=200)
def update_user(user_id: str, request: UpdateUserRequest, db: Session = Depends(get_db)):
    try:
        logger.info("Update user requested", user_id=user_id)
        kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
        user = UserService().update(db, user_id, **kwargs)
        data = _to_user_response(user)
        logger.info("User updated", user_id=user_id)
        return SuccessResponse.ok(data=data.model_dump(), message="User updated successfully")
    except AppException as exc:
        logger.error("AppException in update_user", user_id=user_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in update_user", user_id=user_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())


@router.delete("/{user_id}", status_code=200)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    try:
        logger.info("Delete user requested", user_id=user_id)
        UserService().delete(db, user_id)
        logger.info("User deleted", user_id=user_id)
        return SuccessResponse.ok(data=None, message="User deleted successfully")
    except AppException as exc:
        logger.error("AppException in delete_user", user_id=user_id, error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in delete_user", user_id=user_id, error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())
