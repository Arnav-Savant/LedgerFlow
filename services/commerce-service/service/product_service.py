from sqlalchemy.orm import Session

from config.logger import logger
from models.product import Product
from repository.product_repo import ProductRepo
from utils.common.custom_exception import AppException, ServiceException


class ProductService:
    def __init__(self):
        self.product_repo = ProductRepo()

    def get_by_id(self, db: Session, product_id: str) -> Product:
        try:
            logger.info("Fetching product", product_id=product_id)
            return self.product_repo.get_by_id(db, product_id)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error fetching product", product_id=product_id, error=str(exc))
            raise ServiceException(message="Failed to fetch product", details=str(exc))
