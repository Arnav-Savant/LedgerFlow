from config.database import SessionLocal
from config.logger import logger
from models.user import User
from models.seller import Seller
from models.product import Product
from models.inventory import Inventory
from seeders.seed_data import USERS, SELLERS, PRODUCTS, INVENTORY
from utils.common.custom_exception import DatabaseException


def _seed_users(db) -> None:
    try:
        inserted = 0
        for data in USERS:
            exists = db.query(User).filter(User.email == data["email"]).first()
            if not exists:
                db.add(User(**data))
                inserted += 1
        db.commit()
        logger.info("Users seeded", inserted=inserted, total=len(USERS))
    except Exception as e:
        db.rollback()
        raise DatabaseException(message="Failed to seed users", details=str(e))


def _seed_sellers(db) -> None:
    try:
        inserted = 0
        for data in SELLERS:
            exists = db.query(Seller).filter(Seller.email == data["email"]).first()
            if not exists:
                db.add(Seller(**data))
                inserted += 1
        db.commit()
        logger.info("Sellers seeded", inserted=inserted, total=len(SELLERS))
    except Exception as e:
        db.rollback()
        raise DatabaseException(message="Failed to seed sellers", details=str(e))


def _seed_products(db) -> None:
    try:
        inserted = 0
        for data in PRODUCTS:
            exists = db.query(Product).filter(Product.id == data["id"]).first()
            if not exists:
                db.add(Product(**data))
                inserted += 1
        db.commit()
        logger.info("Products seeded", inserted=inserted, total=len(PRODUCTS))
    except Exception as e:
        db.rollback()
        raise DatabaseException(message="Failed to seed products", details=str(e))


def _seed_inventory(db) -> None:
    try:
        inserted = 0
        for data in INVENTORY:
            exists = db.query(Inventory).filter(Inventory.product_id == data["product_id"]).first()
            if not exists:
                db.add(Inventory(**data))
                inserted += 1
        db.commit()
        logger.info("Inventory seeded", inserted=inserted, total=len(INVENTORY))
    except Exception as e:
        db.rollback()
        raise DatabaseException(message="Failed to seed inventory", details=str(e))


def run_seeders() -> None:
    db = SessionLocal()
    try:
        _seed_users(db)
        _seed_sellers(db)
        _seed_products(db)
        _seed_inventory(db)
    except DatabaseException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Seeder failed, rolling back", error=str(e))
        raise DatabaseException(message="Seeder run failed", details=str(e))
    finally:
        db.close()
