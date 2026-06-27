import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.user import User
from config.logger import logger
from utils.common.custom_exception import DatabaseException, NotFoundException


class UserRepo:
    def create(self, db: Session, name: str, email: str, phone: Optional[str] = None) -> User:
        try:
            user = User(id=str(uuid.uuid4()), name=name, email=email, phone=phone)
            db.add(user)
            db.flush()
            db.refresh(user)
            logger.info("User created", user_id=user.id, email=email)
            return user
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to create user", email=email, error=str(e))
            raise DatabaseException(message="Failed to create user", details=str(e))

    def get_by_id(self, db: Session, user_id: str) -> User:
        try:
            logger.debug("Fetching user by id", user_id=user_id)
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                logger.warning("User not found", user_id=user_id)
                raise NotFoundException("User", user_id)
            return user
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error("Failed to fetch user by id", user_id=user_id, error=str(e))
            raise DatabaseException(message="Failed to fetch user by id", details=str(e))

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        try:
            logger.debug("Fetching user by email", email=email)
            return db.query(User).filter(User.email == email).first()
        except SQLAlchemyError as e:
            logger.error("Failed to fetch user by email", email=email, error=str(e))
            raise DatabaseException(message="Failed to fetch user by email", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        try:
            users = db.query(User).offset(skip).limit(limit).all()
            logger.debug("Fetched all users", count=len(users))
            return users
        except SQLAlchemyError as e:
            logger.error("Failed to fetch users", error=str(e))
            raise DatabaseException(message="Failed to fetch users", details=str(e))

    def update(self, db: Session, user_id: str, **kwargs) -> User:
        try:
            user = self.get_by_id(db, user_id)
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.flush()
            db.refresh(user)
            logger.info("User updated", user_id=user_id)
            return user
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to update user", user_id=user_id, error=str(e))
            raise DatabaseException(message="Failed to update user", details=str(e))

    def delete(self, db: Session, user_id: str) -> None:
        try:
            user = self.get_by_id(db, user_id)
            db.delete(user)
            db.flush()
            logger.info("User deleted", user_id=user_id)
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to delete user", user_id=user_id, error=str(e))
            raise DatabaseException(message="Failed to delete user", details=str(e))
