from pydantic import BaseModel
from utils.enums import Currency


class PaymentSessionInitiateRequest(BaseModel):
    checkout_id: str
    user_id: str
    amount: int
    currency: Currency


class PaymentSessionInitiateResponse(BaseModel):
    session_id: str
    redirect_url: str
