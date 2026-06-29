import enum


class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUND_INITIATED = "REFUND_INITIATED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"
    SUCCESS = "SUCCESS"
    EXPIRED = "EXPIRED"


class AttemptStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PaymentMethod(str, enum.Enum):
    UPI = "UPI"
    CARD = "CARD"
    NET_BANKING = "NET_BANKING"
    WALLET = "WALLET"


class Currency(str, enum.Enum):
    INR = "INR"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    JPY = "JPY"


class RefundStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
