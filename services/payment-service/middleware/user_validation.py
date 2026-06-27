import json

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.database import SessionLocal
from config.logger import logger
from services.user_service import UserService
from utils.common.custom_exception import NotFoundException
from utils.common.error_response import ErrorResponse

# Paths that require user_id validation in the request body.
_VALIDATED_PATHS = {"/api/v1/payment-sessions/initiate"}


class UserValidationMiddleware(BaseHTTPMiddleware):
    """
    Intercepts POST requests to validated paths and checks that the supplied
    user_id exists before the request reaches the route handler.  Returns a
    structured ErrorResponse and short-circuits if the user is not found.

    FastAPI caches the raw request body so the route handler can still read it
    after the middleware has consumed it here.

    A fresh UserService (and its UserRepo) is instantiated per request,
    consistent with how services are instantiated in routes.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path in _VALIDATED_PATHS:
            body_bytes = await request.body()

            try:
                body = json.loads(body_bytes)
            except (json.JSONDecodeError, ValueError):
                logger.warning("Invalid JSON body received", path=request.url.path)
                error = ErrorResponse(
                    success=False,
                    status_code=422,
                    message="Request body must be valid JSON",
                    error="VALIDATION_ERROR",
                )
                return JSONResponse(status_code=422, content=error.model_dump())

            user_id = body.get("user_id")
            if not user_id:
                logger.warning("user_id missing from request body", path=request.url.path)
                error = ErrorResponse(
                    success=False,
                    status_code=422,
                    message="user_id is required",
                    error="VALIDATION_ERROR",
                )
                return JSONResponse(status_code=422, content=error.model_dump())

            db = SessionLocal()
            try:
                UserService().get_by_id(db, user_id)
                logger.info("User validated in middleware", user_id=user_id)
            except NotFoundException:
                logger.warning("User validation failed in middleware", user_id=user_id)
                error = ErrorResponse(
                    success=False,
                    status_code=404,
                    message=f"User '{user_id}' not found",
                    error="NOT_FOUND",
                )
                return JSONResponse(status_code=404, content=error.model_dump())
            except Exception as exc:
                logger.error("Unexpected error during user validation", error=str(exc))
                return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())
            finally:
                db.close()

        return await call_next(request)
