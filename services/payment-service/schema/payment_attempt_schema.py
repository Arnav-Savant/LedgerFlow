from typing import Optional
from pydantic import BaseModel
from utils.enums import PaymentMethod


class PaymentAttemptRequest(BaseModel):
    idempotency_key: str
    payment_method: PaymentMethod


class PaymentAttemptResponse(BaseModel):
    attempt_id: str
    status: str
    failure_reason: Optional[str] = None
    session_status: str
