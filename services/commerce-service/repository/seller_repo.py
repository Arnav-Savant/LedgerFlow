import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.seller import Seller
from utils.common.custom_exception import DatabaseException, NotFoundException


class SellerRepo:
    def create(self, db: Session, name: str, email: str) -> Seller:
        try:
            seller = Seller(id=str(uuid.uuid4()), name=name, email=email)
            db.add(seller)
            db.commit()
            db.refresh(seller)
            return seller
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to create seller", details=str(e))

    def get_by_id(self, db: Session, seller_id: str) -> Seller:
        try:
            seller = db.query(Seller).filter(Seller.id == seller_id).first()
            if seller is None:
                raise NotFoundException(message=f"Seller {seller_id} not found")
            return seller
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch seller by id", details=str(e))

    def get_by_email(self, db: Session, email: str) -> Optional[Seller]:
        try:
            return db.query(Seller).filter(Seller.email == email).first()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch seller by email", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Seller]:
        try:
            return db.query(Seller).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch sellers", details=str(e))

    def update(self, db: Session, seller_id: str, **kwargs) -> Seller:
        try:
            seller = self.get_by_id(db, seller_id)
            for key, value in kwargs.items():
                if hasattr(seller, key):
                    setattr(seller, key, value)
            db.commit()
            db.refresh(seller)
            return seller
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to update seller", details=str(e))

    def delete(self, db: Session, seller_id: str) -> None:
        try:
            seller = self.get_by_id(db, seller_id)
            db.delete(seller)
            db.commit()
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to delete seller", details=str(e))


seller_repo = SellerRepo()
