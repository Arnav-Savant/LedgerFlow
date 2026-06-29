from sqlalchemy.orm import Session

from config.logger import logger
from models.inventory import Inventory
from repository.inventory_repo import InventoryRepo
from utils.common.custom_exception import AppException, ServiceException, NotFoundException, ValidationException


class InventoryService:
    def __init__(self):
        self.inventory_repo = InventoryRepo()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        try:
            logger.info("Fetching all inventory", skip=skip, limit=limit)
            items = self.inventory_repo.get_all(db, skip=skip, limit=limit)
            logger.info("Inventory fetched", count=len(items))
            return items
        except AppException:
            raise
        except Exception as exc:
            raise ServiceException(message="Failed to fetch inventory", details=str(exc))

    def get_by_product_id(self, db: Session, product_id: str) -> Inventory:
        try:
            logger.info("Fetching inventory by product", product_id=product_id)
            inv = self.inventory_repo.get_by_product_id(db, product_id)
            if inv is None:
                raise NotFoundException(message=f"Inventory for product {product_id} not found")
            return inv
        except AppException:
            raise
        except Exception as exc:
            raise ServiceException(message="Failed to fetch inventory by product", details=str(exc))

    def adjust_available(self, db: Session, product_id: str, delta: int) -> Inventory:
        try:
            logger.info("Adjusting inventory", product_id=product_id, delta=delta)
            inv = self.get_by_product_id(db, product_id)
            new_qty = inv.available_quantity + delta
            if new_qty < 0:
                raise ValidationException(
                    message=f"Cannot reduce available quantity below zero (current: {inv.available_quantity}, delta: {delta})"
                )
            inv.available_quantity = new_qty
            db.flush()
            db.refresh(inv)
            db.commit()
            return inv
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to adjust inventory", details=str(exc))

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
