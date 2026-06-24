from pydantic import BaseModel


class ProductDetail(BaseModel):
    product_id: str
    name: str
    price: int
    currency: str


class OrderDetailResponse(BaseModel):
    order_id: str
    checkout_id: str
    user_id: str
    seller_id: str
    amount: int
    currency: str
    order_status: str
    checkout_status: str
    product: ProductDetail
    ledger_updated: bool
    wallet_updated: bool
