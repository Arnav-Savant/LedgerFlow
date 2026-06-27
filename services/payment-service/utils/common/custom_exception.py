from typing import Any, Optional


class AppException(Exception):
    """
    Base exception for all application-level errors.
    Carry status_code, a user-facing message, a machine-readable error code,
    and optional details so the error handler can build a consistent response.
    """

    def __init__(
        self,
        status_code: int = 500,
        message: str = "An unexpected error occurred",
        error: str = "INTERNAL_ERROR",
        details: Optional[Any] = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.error = error
        self.details = details
        super().__init__(message)


class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: Any = None,
        message: Optional[str] = None,
    ) -> None:
        if message is None:
            message = f"{resource} not found"
            if identifier is not None:
                message = f"{resource} '{identifier}' not found"
        super().__init__(status_code=404, message=message, error="NOT_FOUND")


class ConflictException(AppException):
    """Raised when an operation violates a uniqueness or state constraint."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(status_code=409, message=message, error="CONFLICT", details=details)


class ValidationException(AppException):
    """Raised when input data fails domain-level validation."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(status_code=422, message=message, error="VALIDATION_ERROR", details=details)


class DatabaseException(AppException):
    """Raised when a database operation fails at the infrastructure level."""

    def __init__(
        self,
        message: str = "A database error occurred",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(status_code=500, message=message, error="DATABASE_ERROR", details=details)


class ServiceException(AppException):
    """Raised when an unexpected error occurs in the service layer."""

    def __init__(
        self,
        message: str = "A service error occurred",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(status_code=500, message=message, error="SERVICE_ERROR", details=details)


class PaymentException(AppException):
    """Raised when a payment operation fails — provider rejection, gateway error, or invalid state."""

    def __init__(
        self,
        message: str = "Payment processing failed",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(status_code=402, message=message, error="PAYMENT_FAILED", details=details)
