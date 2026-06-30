import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.seller import Seller
from config.logger import logger
from utils.common.custom_exception import DatabaseException, NotFoundException


class SellerRepo:
    def create(self, db: Session, name: str, email: str) -> Seller:
        try:
            seller = Seller(id=str(uuid.uuid4()), name=name, email=email)
            db.add(seller)
            db.flush()
            db.refresh(seller)
            logger.info("Seller created", seller_id=seller.id, email=email)
            return seller
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to create seller", email=email, error=str(e))
            raise DatabaseException(message="Failed to create seller", details=str(e))

    def get_by_id(self, db: Session, seller_id: str) -> Seller:
        try:
            logger.debug("Fetching seller by id", seller_id=seller_id)
            seller = db.query(Seller).filter(Seller.id == seller_id).first()
            if seller is None:
                logger.warning("Seller not found", seller_id=seller_id)
                raise NotFoundException(message=f"Seller {seller_id} not found")
            return seller
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error("Failed to fetch seller by id", seller_id=seller_id, error=str(e))
            raise DatabaseException(message="Failed to fetch seller by id", details=str(e))

    def get_by_email(self, db: Session, email: str) -> Optional[Seller]:
        try:
            logger.debug("Fetching seller by email", email=email)
            return db.query(Seller).filter(Seller.email == email).first()
        except SQLAlchemyError as e:
            logger.error("Failed to fetch seller by email", email=email, error=str(e))
            raise DatabaseException(message="Failed to fetch seller by email", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Seller]:
        try:
            sellers = db.query(Seller).offset(skip).limit(limit).all()
            logger.debug("Fetched all sellers", count=len(sellers))
            return sellers
        except SQLAlchemyError as e:
            logger.error("Failed to fetch sellers", error=str(e))
            raise DatabaseException(message="Failed to fetch sellers", details=str(e))

    def count_all(self, db: Session) -> int:
        try:
            return db.query(Seller).count()
        except SQLAlchemyError as e:
            logger.error("Failed to count records", error=str(e))
            raise DatabaseException(message="Failed to count records", details=str(e))

    def update(self, db: Session, seller_id: str, **kwargs) -> Seller:
        try:
            seller = self.get_by_id(db, seller_id)
            for key, value in kwargs.items():
                if hasattr(seller, key):
                    setattr(seller, key, value)
            db.flush()
            db.refresh(seller)
            logger.info("Seller updated", seller_id=seller_id)
            return seller
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to update seller", seller_id=seller_id, error=str(e))
            raise DatabaseException(message="Failed to update seller", details=str(e))

    def delete(self, db: Session, seller_id: str) -> None:
        try:
            seller = self.get_by_id(db, seller_id)
            db.delete(seller)
            db.flush()
            logger.info("Seller deleted", seller_id=seller_id)
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to delete seller", seller_id=seller_id, error=str(e))
            raise DatabaseException(message="Failed to delete seller", details=str(e))
