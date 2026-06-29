from sqlalchemy.orm import Session

from config.logger import logger
from models.user import User
from repository.user_repo import UserRepo
from utils.common.custom_exception import AppException, ServiceException, ConflictException


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

    def create(self, db: Session, name: str, email: str, phone=None):
        try:
            logger.info("Creating user", email=email)
            existing = self.user_repo.get_by_email(db, email)
            if existing:
                raise ConflictException(message=f"User with email {email} already exists")
            user = self.user_repo.create(db, name=name, email=email, phone=phone)
            db.commit()
            return user
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to create user", details=str(exc))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        try:
            logger.info("Fetching all users", skip=skip, limit=limit)
            users = self.user_repo.get_all(db, skip=skip, limit=limit)
            logger.info("Users fetched", count=len(users))
            return users
        except AppException:
            raise
        except Exception as exc:
            raise ServiceException(message="Failed to fetch users", details=str(exc))

    def update(self, db: Session, user_id: str, **kwargs):
        try:
            logger.info("Updating user", user_id=user_id)
            user = self.user_repo.update(db, user_id, **kwargs)
            db.commit()
            return user
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to update user", details=str(exc))

    def delete(self, db: Session, user_id: str) -> None:
        try:
            logger.info("Deleting user", user_id=user_id)
            self.user_repo.delete(db, user_id)
            db.commit()
        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise ServiceException(message="Failed to delete user", details=str(exc))
