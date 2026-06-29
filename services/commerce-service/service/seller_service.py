from sqlalchemy.orm import Session

from config.logger import logger
from models.seller import Seller
from repository.seller_repo import SellerRepo
from utils.common.custom_exception import AppException, ServiceException, ConflictException


class SellerService:
    def __init__(self):
        self.seller_repo = SellerRepo()

    def create(self, db: Session, name: str, email: str) -> Seller:
        try:
            logger.info("Creating seller", email=email)
            existing = self.seller_repo.get_by_email(db, email)
            if existing:
                raise ConflictException(message=f"Seller with email {email} already exists")
            seller = self.seller_repo.create(db, name=name, email=email)
            db.commit()
            return seller
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to create seller", details=str(exc))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        try:
            logger.info("Fetching all sellers", skip=skip, limit=limit)
            sellers = self.seller_repo.get_all(db, skip=skip, limit=limit)
            logger.info("Sellers fetched", count=len(sellers))
            return sellers
        except AppException:
            raise
        except Exception as exc:
            raise ServiceException(message="Failed to fetch sellers", details=str(exc))

    def get_by_id(self, db: Session, seller_id: str) -> Seller:
        try:
            logger.info("Fetching seller", seller_id=seller_id)
            return self.seller_repo.get_by_id(db, seller_id)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error fetching seller", seller_id=seller_id, error=str(exc))
            raise ServiceException(message="Failed to fetch seller", details=str(exc))

    def update(self, db: Session, seller_id: str, **kwargs) -> Seller:
        try:
            logger.info("Updating seller", seller_id=seller_id)
            seller = self.seller_repo.update(db, seller_id, **kwargs)
            db.commit()
            return seller
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to update seller", details=str(exc))

    def disable(self, db: Session, seller_id: str) -> Seller:
        try:
            logger.info("Disabling seller", seller_id=seller_id)
            seller = self.seller_repo.update(db, seller_id, is_active=False)
            db.commit()
            return seller
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to disable seller", details=str(exc))
