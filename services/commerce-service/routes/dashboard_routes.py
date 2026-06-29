from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.logger import logger
from schema.dashboard_schema import DashboardCountsResponse
from service.dashboard_service import DashboardService
from utils.common.custom_exception import AppException
from utils.common.error_response import ErrorResponse
from utils.common.success_response import SuccessResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/counts", status_code=200)
def get_counts(db: Session = Depends(get_db)):
    try:
        logger.info("Dashboard counts requested")
        counts = DashboardService().get_counts(db)
        data = DashboardCountsResponse(**counts)
        logger.info("Dashboard counts returned")
        return SuccessResponse.ok(data=data.model_dump(), message="Dashboard counts fetched successfully")
    except AppException as exc:
        logger.error("AppException in get_counts", error=exc.error, detail=exc.message)
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse.from_exception(exc).model_dump())
    except Exception as exc:
        logger.exception("Unhandled error in get_counts", error=str(exc))
        return JSONResponse(status_code=500, content=ErrorResponse.internal_error().model_dump())
