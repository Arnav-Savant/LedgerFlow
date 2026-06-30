from sqlalchemy.orm import Session

from config.logger import logger
from models.order import Order
from models.product import Product
from repository.order_repo import OrderRepo
from service.product_service import ProductService
from utils.enums import OrderStatus, CheckoutStatus, Currency
from utils.common.custom_exception import AppException, ServiceException


class OrderService:
    def __init__(self):
        self.order_repo = OrderRepo()
        self.product_service = ProductService()

    # ── Internal mutation methods ─────────────────────────────────────────────
    # These are called from CheckoutService as part of a larger transaction.
    # They flush to the DB session but do NOT commit — CheckoutService owns the
    # transaction boundary and calls db.commit() / db.rollback().

    def create_order(
        self,
        db: Session,
        checkout_id: str,
        user_id: str,
        product_id: str,
        seller_id: str,
        amount: int,
        currency: Currency,
        checkout_status: CheckoutStatus,
        quantity: int = 1,
    ) -> Order:
        try:
            logger.info("Creating order", checkout_id=checkout_id, product_id=product_id)
            return self.order_repo.create(
                db,
                checkout_id=checkout_id,
                user_id=user_id,
                product_id=product_id,
                seller_id=seller_id,
                amount=amount,
                currency=currency,
                checkout_status=checkout_status,
                quantity=quantity,
            )
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error creating order", checkout_id=checkout_id, error=str(exc))
            raise ServiceException(message="Failed to create order", details=str(exc))

    def update_order_status(self, db: Session, order_id: str, status: OrderStatus) -> Order:
        try:
            logger.info("Updating order status", order_id=order_id, status=status)
            return self.order_repo.update_status(db, order_id, status)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error updating order status", order_id=order_id, error=str(exc))
            raise ServiceException(message="Failed to update order status", details=str(exc))

    def get_orders_by_checkout_id(self, db: Session, checkout_id: str) -> list[Order]:
        try:
            logger.info("Fetching orders by checkout", checkout_id=checkout_id)
            return self.order_repo.get_all_by_checkout_id(db, checkout_id)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error fetching orders by checkout", checkout_id=checkout_id, error=str(exc))
            raise ServiceException(message="Failed to fetch orders for checkout", details=str(exc))

    # ── Public read methods ───────────────────────────────────────────────────

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[dict]:
        try:
            logger.info("Fetching all orders", skip=skip, limit=limit)
            orders = self.order_repo.get_all(db, skip=skip, limit=limit)
            result = []
            for order in orders:
                try:
                    product = self.product_service.get_by_id(db, order.product_id)
                    product_name = product.name
                    seller_name = product.seller_id  # fallback
                except Exception:
                    product_name = order.product_id
                    seller_name = order.seller_id
                try:
                    from service.seller_service import SellerService
                    seller = SellerService().get_by_id(db, order.seller_id)
                    seller_name = seller.name
                except Exception:
                    seller_name = order.seller_id
                result.append({
                    "order_id": order.id,
                    "checkout_id": order.checkout_id,
                    "user_id": order.user_id,
                    "product_id": order.product_id,
                    "product_name": product_name,
                    "seller_id": order.seller_id,
                    "seller_name": seller_name,
                    "quantity": order.quantity if hasattr(order, "quantity") else 1,
                    "amount": order.amount,
                    "currency": order.currency.value if hasattr(order.currency, "value") else order.currency,
                    "order_status": order.order_status.value if hasattr(order.order_status, "value") else order.order_status,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                })
            logger.info("Orders fetched", count=len(result))
            return result
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error fetching all orders", error=str(exc))
            raise ServiceException(message="Failed to fetch orders", details=str(exc))

    def count_all(self, db):
        try:
            return self.order_repo.count_all(db)
        except AppException:
            raise
        except Exception as exc:
            raise ServiceException(message="Failed to count orders", details=str(exc))

    def get_by_id(self, db: Session, order_id: str) -> tuple[Order, Product, str]:
        try:
            logger.info("Fetching order", order_id=order_id)
            order = self.order_repo.get_by_id(db, order_id)
            product = self.product_service.get_by_id(db, order.product_id)
            try:
                from service.seller_service import SellerService
                seller = SellerService().get_by_id(db, order.seller_id)
                seller_name = seller.name
            except Exception:
                seller_name = order.seller_id
            return order, product, seller_name
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error fetching order", order_id=order_id, error=str(exc))
            raise ServiceException(message="Failed to fetch order", details=str(exc))
