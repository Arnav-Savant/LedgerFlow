from typing import Optional
from pydantic import BaseModel


class CreateProductRequest(BaseModel):
    seller_id: str
    name: str
    price: int
    currency: str


class UpdateProductRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None


class ProductResponse(BaseModel):
    product_id: str
    seller_id: str
    name: str
    price: int
    currency: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
