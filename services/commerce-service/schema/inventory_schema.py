from typing import Optional
from pydantic import BaseModel


class InventoryResponse(BaseModel):
    inventory_id: str
    product_id: str
    available_quantity: int
    reserved_quantity: int
    updated_at: Optional[str] = None


class AdjustInventoryRequest(BaseModel):
    delta: int
