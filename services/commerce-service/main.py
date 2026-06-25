from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from config.server_config import server_config
from config.logger import logger
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
from utils.common.success_response import SuccessResponse
from middleware.user_validation import UserValidationMiddleware
from routes.checkout_routes import router as checkout_router
from routes.order_routes import router as order_router
import uvicorn


def run_migrations() -> None:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def run_seeders() -> None:
    from seeders.runner import run_seeders as _run
    _run()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running migrations", service=server_config.name)
    run_migrations()
    logger.info("Migrations complete")

    logger.info("Running seeders")
    run_seeders()
    logger.info("Seeders complete")

    logger.info(
        "Service starting",
        service=server_config.name,
        environment=server_config.environment,
        host=server_config.host,
        port=server_config.port,
    )
    yield
    logger.info("Service shutting down", service=server_config.name)


app = FastAPI(
    title=server_config.name,
    debug=server_config.debug,
    lifespan=lifespan,
)

app.add_middleware(UserValidationMiddleware)

_API_PREFIX = "/api/v1"
app.include_router(checkout_router, prefix=_API_PREFIX)
app.include_router(order_router, prefix=_API_PREFIX)


# ── Global exception handlers ─────────────────────────────────────────────────
# These act as a final safety net for any AppException or unknown Exception that
# was NOT caught by a route handler (e.g. raised in middleware or lifespan code).
# Route handlers have their own try/except and return ErrorResponse directly, so
# most exceptions will not reach these handlers during normal request processing.

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    error = ErrorResponse.from_exception(exc)
    logger.error(
        "Unhandled AppException",
        path=request.url.path,
        status_code=error.status_code,
        error=error.error,
        message=error.message,
    )
    return JSONResponse(status_code=error.status_code, content=error.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error = ErrorResponse.internal_error()
    logger.exception("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content=error.model_dump())


@app.get("/health")
async def health():
    logger.info("Health check requested", service=server_config.name)
    data = {
        "service": server_config.name,
        "environment": server_config.environment,
        "status": "ok",
    }
    return SuccessResponse.ok(data=data, message="Service is healthy")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        reload=server_config.reload,
        log_level=server_config.log_level.lower(),
    )
