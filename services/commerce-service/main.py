from contextlib import asynccontextmanager
from fastapi import FastAPI
from config.server_config import server_config
from config.logger import logger
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
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
