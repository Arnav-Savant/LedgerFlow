from sqlalchemy.orm import Session

from config.logger import logger
from repository.user_repo import UserRepo
from repository.seller_repo import SellerRepo
from repository.product_repo import ProductRepo
from repository.checkout_repo import CheckoutRepo
from repository.order_repo import OrderRepo
from utils.common.custom_exception import AppException, ServiceException


class DashboardService:
    def __init__(self):
        self.user_repo = UserRepo()
        self.seller_repo = SellerRepo()
        self.product_repo = ProductRepo()
        self.checkout_repo = CheckoutRepo()
        self.order_repo = OrderRepo()

    def get_counts(self, db: Session) -> dict:
        try:
            logger.info("Fetching dashboard counts")
            users = self.user_repo.get_all(db, skip=0, limit=100000)
            sellers = self.seller_repo.get_all(db, skip=0, limit=100000)
            products = self.product_repo.get_all(db, skip=0, limit=100000)
            checkouts = self.checkout_repo.get_all(db, skip=0, limit=100000)
            orders = self.order_repo.get_all(db, skip=0, limit=100000)
            counts = {
                "total_users": len(users),
                "total_sellers": len(sellers),
                "total_active_sellers": sum(1 for s in sellers if s.is_active),
                "total_products": len(products),
                "total_active_products": sum(1 for p in products if p.is_active),
                "total_checkouts": len(checkouts),
                "total_orders": len(orders),
            }
            logger.info("Dashboard counts fetched", **counts)
            return counts
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error fetching dashboard counts", error=str(exc))
            raise ServiceException(message="Failed to fetch dashboard counts", details=str(exc))
