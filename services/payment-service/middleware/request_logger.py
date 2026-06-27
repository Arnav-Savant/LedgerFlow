import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from config.logger import logger


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        logger.info(
            "Incoming request",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
        )
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "Request failed with unhandled exception",
                method=request.method,
                path=request.url.path,
                elapsed_ms=elapsed,
                error=str(exc),
            )
            raise
        elapsed = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed,
        )
        return response
