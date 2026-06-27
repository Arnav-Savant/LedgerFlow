from sqlalchemy.orm import Session
from config.logger import logger
from models.user import User
from repository.user_repo import UserRepo
from utils.common.custom_exception import AppException, ServiceException


class UserService:
    def __init__(self):
        self.user_repo = UserRepo()

    def get_by_id(self, db: Session, user_id: str) -> User:
        try:
            logger.info("Fetching user", user_id=user_id)
            return self.user_repo.get_by_id(db, user_id)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Unexpected error fetching user", user_id=user_id, error=str(exc))
            raise ServiceException(message="Failed to fetch user", details=str(exc))
