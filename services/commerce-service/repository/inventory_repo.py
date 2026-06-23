import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.inventory import Inventory
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
            db.commit()
            db.refresh(inventory)
            return inventory
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to create inventory", details=str(e))

    def get_by_id(self, db: Session, inventory_id: str) -> Inventory:
        try:
            inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
            if inventory is None:
                raise NotFoundException(message=f"Inventory {inventory_id} not found")
            return inventory
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch inventory by id", details=str(e))

    def get_by_product_id(self, db: Session, product_id: str) -> Optional[Inventory]:
        try:
            return db.query(Inventory).filter(Inventory.product_id == product_id).first()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch inventory by product", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Inventory]:
        try:
            return db.query(Inventory).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch inventory", details=str(e))

    def reserve(self, db: Session, product_id: str, quantity: int) -> Inventory:
        """Move `quantity` units from available → reserved. Raises InsufficientStockException if stock is low."""
        try:
            inventory = self.get_by_product_id(db, product_id)
            if inventory is None:
                raise NotFoundException(message=f"Inventory for product {product_id} not found")
            if inventory.available_quantity < quantity:
                raise InsufficientStockException(
                    details={
                        "product_id": product_id,
                        "requested": quantity,
                        "available": inventory.available_quantity,
                    }
                )
            inventory.available_quantity -= quantity
            inventory.reserved_quantity += quantity
            db.commit()
            db.refresh(inventory)
            return inventory
        except (NotFoundException, InsufficientStockException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to reserve inventory", details=str(e))

    def release(self, db: Session, product_id: str, quantity: int) -> Inventory:
        """Move `quantity` units from reserved → available (on payment failure or cancellation)."""
        try:
            inventory = self.get_by_product_id(db, product_id)
            if inventory is None:
                raise NotFoundException(message=f"Inventory for product {product_id} not found")
            if inventory.reserved_quantity < quantity:
                raise DatabaseException(
                    message="Cannot release more units than reserved",
                    details={"product_id": product_id, "requested": quantity, "reserved": inventory.reserved_quantity},
                )
            inventory.reserved_quantity -= quantity
            inventory.available_quantity += quantity
            db.commit()
            db.refresh(inventory)
            return inventory
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to release inventory", details=str(e))

    def commit_reservation(self, db: Session, product_id: str, quantity: int) -> Inventory:
        """Consume `quantity` units from reserved (on payment success). Stock is permanently gone."""
        try:
            inventory = self.get_by_product_id(db, product_id)
            if inventory is None:
                raise NotFoundException(message=f"Inventory for product {product_id} not found")
            if inventory.reserved_quantity < quantity:
                raise DatabaseException(
                    message="Cannot commit more units than reserved",
                    details={"product_id": product_id, "requested": quantity, "reserved": inventory.reserved_quantity},
                )
            inventory.reserved_quantity -= quantity
            db.commit()
            db.refresh(inventory)
            return inventory
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to commit inventory reservation", details=str(e))

    def delete(self, db: Session, inventory_id: str) -> None:
        try:
            inventory = self.get_by_id(db, inventory_id)
            db.delete(inventory)
            db.commit()
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to delete inventory", details=str(e))


inventory_repo = InventoryRepo()
