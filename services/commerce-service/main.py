from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from config.server_config import server_config
from config.logger import logger
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
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


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    error = ErrorResponse.from_exception(exc)
    logger.error(
        "AppException raised",
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
    return {
        "status": "ok",
        "service": server_config.name,
        "environment": server_config.environment,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        reload=server_config.reload,
        log_level=server_config.log_level.lower(),
    )
