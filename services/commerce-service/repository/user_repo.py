import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.user import User
from utils.common.custom_exception import DatabaseException, NotFoundException


class UserRepo:
    def create(self, db: Session, name: str, email: str, phone: Optional[str] = None) -> User:
        try:
            user = User(id=str(uuid.uuid4()), name=name, email=email, phone=phone)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to create user", details=str(e))

    def get_by_id(self, db: Session, user_id: str) -> User:
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise NotFoundException(message=f"User {user_id} not found")
            return user
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch user by id", details=str(e))

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        try:
            return db.query(User).filter(User.email == email).first()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch user by email", details=str(e))

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        try:
            return db.query(User).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            raise DatabaseException(message="Failed to fetch users", details=str(e))

    def update(self, db: Session, user_id: str, **kwargs) -> User:
        try:
            user = self.get_by_id(db, user_id)
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.commit()
            db.refresh(user)
            return user
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to update user", details=str(e))

    def delete(self, db: Session, user_id: str) -> None:
        try:
            user = self.get_by_id(db, user_id)
            db.delete(user)
            db.commit()
        except (NotFoundException, DatabaseException):
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise DatabaseException(message="Failed to delete user", details=str(e))


user_repo = UserRepo()
