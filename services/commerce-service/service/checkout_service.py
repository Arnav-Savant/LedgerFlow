from typing import Any
from sqlalchemy.orm import Session

from config.logger import logger
from models.checkout import Checkout
from models.order import Order
from repository.checkout_repo import CheckoutRepo
from service.order_service import OrderService
from service.product_service import ProductService
from service.inventory_service import InventoryService
from utils.enums import CheckoutStatus, OrderStatus
from utils.common.custom_exception import AppException, ServiceException


class CheckoutService:
    def __init__(self):
        self.checkout_repo = CheckoutRepo()
        self.order_service = OrderService()
        self.product_service = ProductService()
        self.inventory_service = InventoryService()

    def initiate_checkout(
        self,
        db: Session,
        user_id: str,
        products: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Orchestrates the full checkout initiation flow as a single DB transaction.

        Steps:
          1. Create PENDING checkout record (flush).
          2. For each product: fetch details then reserve inventory (flush).
          3. Create one Order per product (flush).
          4. Payment initiation placeholder.
          5. Transition all orders → PAYMENT_PENDING (flush).
          6. Update checkout total_amount and status → PAYMENT_INITIATED (flush).
          7. db.commit() — all steps land atomically.

        On any failure: db.rollback() undoes every flush in one shot.
        No compensating transactions needed.
        """
        try:
            # Step 1: Create checkout record with placeholder total_amount=0
            checkout = self.checkout_repo.create(db, user_id=user_id, total_amount=0)
            logger.info("Checkout created", checkout_id=checkout.id, user_id=user_id)

            # Step 2: For each product, fetch details and reserve inventory
            orders_data: list[dict[str, Any]] = []
            total_amount = 0

            for item in products:
                product_id: str = item["product_id"]
                quantity: int = item["quantity"]

                product = self.product_service.get_by_id(db, product_id)
                self.inventory_service.reserve(db, product_id, quantity)
                logger.info("Inventory reserved", product_id=product_id, quantity=quantity)

                amount = product.price * quantity
                total_amount += amount
                orders_data.append({
                    "product_id": product.id,
                    "seller_id": product.seller_id,
                    "amount": amount,
                    "currency": product.currency,
                })

            # Step 3: Create one order per product
            created_orders: list[Order] = []
            for order_data in orders_data:
                order = self.order_service.create_order(
                    db,
                    checkout_id=checkout.id,
                    user_id=user_id,
                    product_id=order_data["product_id"],
                    seller_id=order_data["seller_id"],
                    amount=order_data["amount"],
                    currency=order_data["currency"],
                    checkout_status=checkout.status,
                )
                created_orders.append(order)
                logger.info("Order created", order_id=order.id, product_id=order_data["product_id"])

            # Step 4: Payment initiation placeholder
            # ── FUTURE INTEGRATION POINT ──────────────────────────────────────────
            # When the Payment Service is available, publish a CheckoutPaymentRequested
            # event here (via transactional outbox) instead of this log statement.
            logger.info(
                "Payment initiation placeholder. Future Payment Service integration point.",
                checkout_id=checkout.id,
            )
            # ──────────────────────────────────────────────────────────────────────

            # Step 5: Transition all orders → PAYMENT_PENDING
            for order in created_orders:
                self.order_service.update_order_status(db, order.id, OrderStatus.PAYMENT_PENDING)
                logger.info("Order status updated", order_id=order.id, status=OrderStatus.PAYMENT_PENDING)

            # Step 6: Update checkout with final total and status → PAYMENT_INITIATED
            updated_checkout = self.checkout_repo.update(
                db,
                checkout.id,
                total_amount=total_amount,
                status=CheckoutStatus.PAYMENT_INITIATED,
            )
            logger.info(
                "Checkout finalised",
                checkout_id=checkout.id,
                total_amount=total_amount,
                status=CheckoutStatus.PAYMENT_INITIATED,
            )

            # Step 7: Commit all flushes atomically
            db.commit()
            logger.info("Checkout transaction committed", checkout_id=checkout.id)

            # Fetch final state post-commit (session objects are expired after commit)
            updated_orders = self.order_service.get_orders_by_checkout_id(db, checkout.id)

            return {"checkout": updated_checkout, "orders": updated_orders}

        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            logger.exception("Unexpected error in initiate_checkout", user_id=user_id, error=str(exc))
            raise ServiceException(message="Failed to initiate checkout", details=str(exc))

    def get_checkout(self, db: Session, checkout_id: str) -> tuple[Checkout, list[Order]]:
        try:
            logger.info("Fetching checkout", checkout_id=checkout_id)
            checkout = self.checkout_repo.get_by_id(db, checkout_id)
            orders = self.order_service.get_orders_by_checkout_id(db, checkout_id)
            return checkout, orders
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error fetching checkout", checkout_id=checkout_id, error=str(exc))
            raise ServiceException(message="Failed to fetch checkout", details=str(exc))
