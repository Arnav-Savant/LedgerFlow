from typing import Optional
from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    phone: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
