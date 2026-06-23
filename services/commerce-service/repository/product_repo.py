import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.product import Product
from utils.enums import Currency
from utils.common.custom_exception import DatabaseException, NotFoundException


class ProductRepo:
    def create(self, db: Session, seller_id: str, name: str, price: int, currency: Currency) -> Product:
        try:
            product = Product(id=str(uuid.uuid4()), seller_id=seller_id, name=name, price=price, currency=currency)
            db.add(product)
            db.commit()
            db.refresh(product)
            return product
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to create product", details=str(e))

    def get_by_id(self, db: Session, product_id: str) -> Product:
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product is None:
                raise NotFoundException(message=f"Product {product_id} not found")
            return product
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch product by id", details=str(e))

    def get_by_seller(self, db: Session, seller_id: str) -> list[Product]:
        try:
            return db.query(Product).filter(Product.seller_id == seller_id).all()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch products by seller", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Product]:
        try:
            return db.query(Product).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch products", details=str(e))

    def update(self, db: Session, product_id: str, **kwargs) -> Product:
        try:
            product = self.get_by_id(db, product_id)
            for key, value in kwargs.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            db.commit()
            db.refresh(product)
            return product
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to update product", details=str(e))

    def delete(self, db: Session, product_id: str) -> None:
        try:
            product = self.get_by_id(db, product_id)
            db.delete(product)
            db.commit()
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to delete product", details=str(e))


product_repo = ProductRepo()
