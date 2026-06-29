from sqlalchemy.orm import Session

from config.logger import logger
from models.product import Product
from repository.product_repo import ProductRepo
from utils.common.custom_exception import AppException, ServiceException, ValidationException


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

    def create(self, db: Session, seller_id: str, name: str, price: int, currency: str) -> Product:
        try:
            logger.info("Creating product", seller_id=seller_id, name=name)
            from service.seller_service import SellerService
            seller = SellerService().get_by_id(db, seller_id)
            if not seller.is_active:
                raise ValidationException(message=f"Seller {seller_id} is not active")
            from utils.enums import Currency
            currency_enum = Currency(currency) if isinstance(currency, str) else currency
            product = self.product_repo.create(db, seller_id=seller_id, name=name, price=price, currency=currency_enum)
            db.commit()
            return product
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to create product", details=str(exc))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        try:
            logger.info("Fetching all products", skip=skip, limit=limit)
            products = self.product_repo.get_all(db, skip=skip, limit=limit)
            logger.info("Products fetched", count=len(products))
            return products
        except AppException:
            raise
        except Exception as exc:
            raise ServiceException(message="Failed to fetch products", details=str(exc))

    def update(self, db: Session, product_id: str, **kwargs) -> Product:
        try:
            logger.info("Updating product", product_id=product_id)
            product = self.product_repo.update(db, product_id, **kwargs)
            db.commit()
            return product
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to update product", details=str(exc))

    def deactivate(self, db: Session, product_id: str) -> Product:
        try:
            logger.info("Deactivating product", product_id=product_id)
            product = self.product_repo.update(db, product_id, is_active=False)
            db.commit()
            return product
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to deactivate product", details=str(exc))
