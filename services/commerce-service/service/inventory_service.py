from sqlalchemy.orm import Session

from config.logger import logger
from models.inventory import Inventory
from repository.inventory_repo import InventoryRepo
from utils.common.custom_exception import AppException, ServiceException


class InventoryService:
    def __init__(self):
        self.inventory_repo = InventoryRepo()

    def reserve(self, db: Session, product_id: str, quantity: int) -> Inventory:
        try:
            logger.info("Reserving inventory", product_id=product_id, quantity=quantity)
            return self.inventory_repo.reserve(db, product_id, quantity)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error reserving inventory", product_id=product_id, error=str(exc))
            raise ServiceException(message="Failed to reserve inventory", details=str(exc))

    def release(self, db: Session, product_id: str, quantity: int) -> Inventory:
        try:
            logger.info("Releasing inventory", product_id=product_id, quantity=quantity)
            return self.inventory_repo.release(db, product_id, quantity)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error releasing inventory", product_id=product_id, error=str(exc))
            raise ServiceException(message="Failed to release inventory", details=str(exc))

    def commit_reservation(self, db: Session, product_id: str, quantity: int) -> Inventory:
        try:
            logger.info("Committing inventory reservation", product_id=product_id, quantity=quantity)
            return self.inventory_repo.commit_reservation(db, product_id, quantity)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error committing reservation", product_id=product_id, error=str(exc))
            raise ServiceException(message="Failed to commit inventory reservation", details=str(exc))
