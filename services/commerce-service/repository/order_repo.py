import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.order import Order
from utils.enums import OrderStatus, CheckoutStatus, Currency
from config.logger import logger
from utils.common.custom_exception import DatabaseException, NotFoundException


class OrderRepo:
    def create(
        self,
        db: Session,
        checkout_id: str,
        user_id: str,
        product_id: str,
        seller_id: str,
        amount: int,
        currency: Currency,
        checkout_status: CheckoutStatus,
    ) -> Order:
        try:
            order = Order(
                id=str(uuid.uuid4()),
                checkout_id=checkout_id,
                user_id=user_id,
                product_id=product_id,
                seller_id=seller_id,
                amount=amount,
                currency=currency,
                order_status=OrderStatus.CREATED,
                checkout_status=checkout_status,
                ledger_updated=False,
                wallet_updated=False,
            )
            db.add(order)
            db.flush()
            db.refresh(order)
            logger.info("Order record created", order_id=order.id, checkout_id=checkout_id, product_id=product_id)
            return order
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to create order", checkout_id=checkout_id, product_id=product_id, error=str(e))
            raise DatabaseException(message="Failed to create order", details=str(e))

    def get_by_id(self, db: Session, order_id: str) -> Order:
        try:
            logger.debug("Fetching order by id", order_id=order_id)
            order = db.query(Order).filter(Order.id == order_id).first()
            if order is None:
                logger.warning("Order not found", order_id=order_id)
                raise NotFoundException(message=f"Order {order_id} not found")
            return order
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error("Failed to fetch order by id", order_id=order_id, error=str(e))
            raise DatabaseException(message="Failed to fetch order by id", details=str(e))

    def get_by_checkout_id(self, db: Session, checkout_id: str) -> Optional[Order]:
        try:
            logger.debug("Fetching order by checkout id", checkout_id=checkout_id)
            return db.query(Order).filter(Order.checkout_id == checkout_id).first()
        except SQLAlchemyError as e:
            logger.error("Failed to fetch order by checkout", checkout_id=checkout_id, error=str(e))
            raise DatabaseException(message="Failed to fetch order by checkout", details=str(e))

    def get_all_by_checkout_id(self, db: Session, checkout_id: str) -> list[Order]:
        try:
            orders = db.query(Order).filter(Order.checkout_id == checkout_id).all()
            logger.debug("Fetched all orders by checkout", checkout_id=checkout_id, count=len(orders))
            return orders
        except SQLAlchemyError as e:
            logger.error("Failed to fetch orders by checkout", checkout_id=checkout_id, error=str(e))
            raise DatabaseException(message="Failed to fetch orders by checkout", details=str(e))

    def get_by_user_id(self, db: Session, user_id: str) -> list[Order]:
        try:
            orders = db.query(Order).filter(Order.user_id == user_id).all()
            logger.debug("Fetched orders by user", user_id=user_id, count=len(orders))
            return orders
        except SQLAlchemyError as e:
            logger.error("Failed to fetch orders by user", user_id=user_id, error=str(e))
            raise DatabaseException(message="Failed to fetch orders by user", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Order]:
        try:
            orders = db.query(Order).offset(skip).limit(limit).all()
            logger.debug("Fetched all orders", count=len(orders))
            return orders
        except SQLAlchemyError as e:
            logger.error("Failed to fetch orders", error=str(e))
            raise DatabaseException(message="Failed to fetch orders", details=str(e))

    def update_status(self, db: Session, order_id: str, status: OrderStatus) -> Order:
        try:
            order = self.get_by_id(db, order_id)
            order.order_status = status
            db.flush()
            db.refresh(order)
            logger.info("Order status updated", order_id=order_id, status=status)
            return order
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to update order status", order_id=order_id, error=str(e))
            raise DatabaseException(message="Failed to update order status", details=str(e))

    def mark_ledger_updated(self, db: Session, order_id: str) -> Order:
        try:
            order = self.get_by_id(db, order_id)
            order.ledger_updated = True
            db.flush()
            db.refresh(order)
            logger.info("Order ledger marked updated", order_id=order_id)
            return order
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to mark order ledger updated", order_id=order_id, error=str(e))
            raise DatabaseException(message="Failed to mark order ledger updated", details=str(e))

    def mark_wallet_updated(self, db: Session, order_id: str) -> Order:
        try:
            order = self.get_by_id(db, order_id)
            order.wallet_updated = True
            db.flush()
            db.refresh(order)
            logger.info("Order wallet marked updated", order_id=order_id)
            return order
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to mark order wallet updated", order_id=order_id, error=str(e))
            raise DatabaseException(message="Failed to mark order wallet updated", details=str(e))

    def delete(self, db: Session, order_id: str) -> None:
        try:
            order = self.get_by_id(db, order_id)
            db.delete(order)
            db.flush()
            logger.info("Order deleted", order_id=order_id)
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to delete order", order_id=order_id, error=str(e))
            raise DatabaseException(message="Failed to delete order", details=str(e))
