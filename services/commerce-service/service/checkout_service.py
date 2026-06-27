import json
import urllib.request
import urllib.error
from typing import Any
from sqlalchemy.orm import Session

from config.logger import logger
from config.server_config import server_config
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

    def _call_payment_service(
        self,
        checkout_id: str,
        user_id: str,
        amount: int,
        currency: str,
    ) -> dict[str, str]:
        """
        Calls the payment service to create a PaymentSession.
        Returns {"session_id": ..., "redirect_url": ...}.
        Raises ServiceException on any failure so the caller can rollback.
        """
        url = (
            f"http://{server_config.payment_service_host}"
            f":{server_config.payment_service_port}"
            f"/api/v1/payment-sessions/initiate"
        )
        payload = json.dumps({
            "checkout_id": checkout_id,
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            logger.info(
                "Calling payment service to initiate session",
                checkout_id=checkout_id,
                url=url,
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))

            data = body.get("data", {})
            session_id = data.get("session_id")
            redirect_url = data.get("redirect_url")

            if not session_id or not redirect_url:
                logger.error(
                    "Payment service response missing required fields",
                    checkout_id=checkout_id,
                    response=body,
                )
                raise ServiceException(
                    message="Payment service returned an incomplete response",
                    details=body,
                )

            logger.info(
                "Payment session created",
                checkout_id=checkout_id,
                session_id=session_id,
            )
            return {"session_id": session_id, "redirect_url": redirect_url}

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            logger.error(
                "Payment service returned HTTP error",
                checkout_id=checkout_id,
                status=e.code,
                error=error_body,
            )
            raise ServiceException(
                message=f"Payment service error: HTTP {e.code}",
                details=error_body,
            )
        except urllib.error.URLError as e:
            logger.error(
                "Could not reach payment service",
                checkout_id=checkout_id,
                error=str(e.reason),
            )
            raise ServiceException(
                message="Payment service is unreachable",
                details=str(e.reason),
            )

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
          4. Call payment service → receive session_id + redirect_url.
          5. Store payment_session_id on checkout (flush).
          6. Transition all orders → PAYMENT_PENDING (flush).
          7. Update checkout total_amount and status → PAYMENT_INITIATED (flush).
          8. db.commit() — all steps land atomically.

        On any failure: db.rollback() undoes every flush in one shot.
        Note: the payment session created in step 4 is committed independently
        by the payment service. An orphaned session may exist if step 8 fails —
        this is an accepted tradeoff until the transactional outbox is implemented.
        """
        try:
            # Step 1: Create checkout with placeholder total_amount=0
            checkout = self.checkout_repo.create(db, user_id=user_id, total_amount=0)
            logger.info("Checkout created", checkout_id=checkout.id, user_id=user_id)

            # Step 2: Fetch product details and reserve inventory
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

            # Step 4: Call payment service — use first product's currency for the session
            primary_currency = str(orders_data[0]["currency"].value if hasattr(orders_data[0]["currency"], "value") else orders_data[0]["currency"])
            payment_result = self._call_payment_service(
                checkout_id=checkout.id,
                user_id=user_id,
                amount=total_amount,
                currency=primary_currency,
            )
            session_id = payment_result["session_id"]
            redirect_url = payment_result["redirect_url"]

            # Step 5: Store payment_session_id on the checkout record
            self.checkout_repo.set_payment_session(db, checkout.id, session_id)

            # Step 6: Transition all orders → PAYMENT_PENDING
            for order in created_orders:
                self.order_service.update_order_status(db, order.id, OrderStatus.PAYMENT_PENDING)
                logger.info("Order status updated", order_id=order.id, status=OrderStatus.PAYMENT_PENDING)

            # Step 7: Update checkout with final total and status → PAYMENT_INITIATED
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

            # Step 8: Commit all flushes atomically
            db.commit()
            logger.info("Checkout transaction committed", checkout_id=checkout.id)

            updated_orders = self.order_service.get_orders_by_checkout_id(db, checkout.id)

            return {
                "checkout": updated_checkout,
                "orders": updated_orders,
                "payment_session_id": session_id,
                "redirect_url": redirect_url,
            }

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
