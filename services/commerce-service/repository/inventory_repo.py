import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.inventory import Inventory
from config.logger import logger
from utils.common.custom_exception import DatabaseException, NotFoundException, InsufficientStockException


class InventoryRepo:
    def create(self, db: Session, product_id: str, available_quantity: int) -> Inventory:
        try:
            inventory = Inventory(
                id=str(uuid.uuid4()),
                product_id=product_id,
                available_quantity=available_quantity,
                reserved_quantity=0,
            )
            db.add(inventory)
            db.flush()
            db.refresh(inventory)
            logger.info("Inventory created", inventory_id=inventory.id, product_id=product_id, available_quantity=available_quantity)
            return inventory
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to create inventory", product_id=product_id, error=str(e))
            raise DatabaseException(message="Failed to create inventory", details=str(e))

    def get_by_id(self, db: Session, inventory_id: str) -> Inventory:
        try:
            logger.debug("Fetching inventory by id", inventory_id=inventory_id)
            inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
            if inventory is None:
                logger.warning("Inventory not found", inventory_id=inventory_id)
                raise NotFoundException(message=f"Inventory {inventory_id} not found")
            return inventory
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error("Failed to fetch inventory by id", inventory_id=inventory_id, error=str(e))
            raise DatabaseException(message="Failed to fetch inventory by id", details=str(e))

    def get_by_product_id(self, db: Session, product_id: str) -> Optional[Inventory]:
        try:
            logger.debug("Fetching inventory by product id", product_id=product_id)
            return db.query(Inventory).filter(Inventory.product_id == product_id).first()
        except SQLAlchemyError as e:
            logger.error("Failed to fetch inventory by product", product_id=product_id, error=str(e))
            raise DatabaseException(message="Failed to fetch inventory by product", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Inventory]:
        try:
            items = db.query(Inventory).offset(skip).limit(limit).all()
            logger.debug("Fetched all inventory", count=len(items))
            return items
        except SQLAlchemyError as e:
            logger.error("Failed to fetch inventory", error=str(e))
            raise DatabaseException(message="Failed to fetch inventory", details=str(e))

    def count_all(self, db: Session) -> int:
        try:
            return db.query(Inventory).count()
        except SQLAlchemyError as e:
            logger.error("Failed to count records", error=str(e))
            raise DatabaseException(message="Failed to count records", details=str(e))

    def reserve(self, db: Session, product_id: str, quantity: int) -> Inventory:
        """Move `quantity` units from available → reserved. Raises InsufficientStockException if stock is low."""
        try:
            inventory = self.get_by_product_id(db, product_id)
            if inventory is None:
                logger.warning("Inventory not found for reservation", product_id=product_id)
                raise NotFoundException(message=f"Inventory for product {product_id} not found")
            if inventory.available_quantity < quantity:
                logger.warning(
                    "Insufficient stock for reservation",
                    product_id=product_id,
                    requested=quantity,
                    available=inventory.available_quantity,
                )
                raise InsufficientStockException(
                    details={
                        "product_id": product_id,
                        "requested": quantity,
                        "available": inventory.available_quantity,
                    }
                )
            inventory.available_quantity -= quantity
            inventory.reserved_quantity += quantity
            db.flush()
            db.refresh(inventory)
            logger.info("Inventory reserved", product_id=product_id, quantity=quantity, remaining=inventory.available_quantity)
            return inventory
        except (NotFoundException, InsufficientStockException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to reserve inventory", product_id=product_id, error=str(e))
            raise DatabaseException(message="Failed to reserve inventory", details=str(e))

    def release(self, db: Session, product_id: str, quantity: int) -> Inventory:
        """Move `quantity` units from reserved → available (on payment failure or cancellation)."""
        try:
            inventory = self.get_by_product_id(db, product_id)
            if inventory is None:
                logger.warning("Inventory not found for release", product_id=product_id)
                raise NotFoundException(message=f"Inventory for product {product_id} not found")
            if inventory.reserved_quantity < quantity:
                logger.error(
                    "Cannot release more units than reserved",
                    product_id=product_id,
                    requested=quantity,
                    reserved=inventory.reserved_quantity,
                )
                raise DatabaseException(
                    message="Cannot release more units than reserved",
                    details={"product_id": product_id, "requested": quantity, "reserved": inventory.reserved_quantity},
                )
            inventory.reserved_quantity -= quantity
            inventory.available_quantity += quantity
            db.flush()
            db.refresh(inventory)
            logger.info("Inventory released", product_id=product_id, quantity=quantity)
            return inventory
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to release inventory", product_id=product_id, error=str(e))
            raise DatabaseException(message="Failed to release inventory", details=str(e))

    def commit_reservation(self, db: Session, product_id: str, quantity: int) -> Inventory:
        """Consume `quantity` units from reserved (on payment success). Stock is permanently gone."""
        try:
            inventory = self.get_by_product_id(db, product_id)
            if inventory is None:
                logger.warning("Inventory not found for commit", product_id=product_id)
                raise NotFoundException(message=f"Inventory for product {product_id} not found")
            if inventory.reserved_quantity < quantity:
                logger.error(
                    "Cannot commit more units than reserved",
                    product_id=product_id,
                    requested=quantity,
                    reserved=inventory.reserved_quantity,
                )
                raise DatabaseException(
                    message="Cannot commit more units than reserved",
                    details={"product_id": product_id, "requested": quantity, "reserved": inventory.reserved_quantity},
                )
            inventory.reserved_quantity -= quantity
            db.flush()
            db.refresh(inventory)
            logger.info("Inventory reservation committed", product_id=product_id, quantity=quantity)
            return inventory
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to commit inventory reservation", product_id=product_id, error=str(e))
            raise DatabaseException(message="Failed to commit inventory reservation", details=str(e))

    def delete(self, db: Session, inventory_id: str) -> None:
        try:
            inventory = self.get_by_id(db, inventory_id)
            db.delete(inventory)
            db.flush()
            logger.info("Inventory deleted", inventory_id=inventory_id)
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to delete inventory", inventory_id=inventory_id, error=str(e))
            raise DatabaseException(message="Failed to delete inventory", details=str(e))
