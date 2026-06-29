from typing import Optional
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


class AttemptSummary(BaseModel):
    attempt_id: str
    status: str
    failure_reason: Optional[str] = None
    created_at: str


class PaymentSessionDetailResponse(BaseModel):
    session_id: str
    status: str
    amount: int
    currency: str
    payment_method: Optional[str] = None
    attempt_count: int
    max_attempts: int
    expires_at: str
    ui_state: str
    can_retry: bool
    attempts: list[AttemptSummary]


class PaymentSessionListItemResponse(BaseModel):
    session_id: str
    checkout_id: str
    user_id: str
    status: str
    amount: int
    currency: str
    attempt_count: int
    max_attempts: int
    expires_at: str
    ui_state: str
    can_retry: bool
    redirect_url: str
    created_at: Optional[str] = None
