from typing import Optional
from pydantic import BaseModel


class CreateSellerRequest(BaseModel):
    name: str
    email: str


class UpdateSellerRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class SellerResponse(BaseModel):
    seller_id: str
    name: str
    email: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
