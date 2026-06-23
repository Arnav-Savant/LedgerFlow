import enum


class CheckoutStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    REFUND_INITIATED = "REFUND_INITIATED"
    REFUNDED = "REFUNDED"
    


class Currency(str, enum.Enum):
    INR = "INR"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    JPY = "JPY"

