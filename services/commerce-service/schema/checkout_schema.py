from pydantic import BaseModel, Field


class ProductItem(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, description="Must be at least 1")


class CheckoutInitiateRequest(BaseModel):
    user_id: str
    products: list[ProductItem] = Field(min_length=1, description="At least one product required")


# ── Response schemas ──────────────────────────────────────────────────────────

class OrderSummary(BaseModel):
    order_id: str
    product_id: str
    seller_id: str
    amount: int
    currency: str
    order_status: str


class CheckoutInitiateResponse(BaseModel):
    checkout_id: str
    user_id: str
    checkout_status: str
    total_amount: int
    order_ids: list[str]
    orders: list[OrderSummary]


class CheckoutDetailResponse(BaseModel):
    checkout_id: str
    user_id: str
    checkout_status: str
    total_amount: int
    orders: list[OrderSummary]
