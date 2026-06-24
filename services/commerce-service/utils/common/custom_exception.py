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
        # Supports both NotFoundException(resource, identifier) and
        # the legacy NotFoundException(message="...") calling convention.
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


class InsufficientStockException(AppException):
    """Raised when requested inventory quantity exceeds available stock."""

    def __init__(
        self,
        product_id: Any = None,
        requested: Optional[int] = None,
        available: Optional[int] = None,
        details: Optional[Any] = None,
    ) -> None:
        # Supports both InsufficientStockException(product_id, requested, available)
        # and the legacy InsufficientStockException(details={...}) calling convention.
        if details is None and product_id is not None:
            details = {
                "product_id": str(product_id),
                "requested": requested,
                "available": available,
            }
        super().__init__(
            status_code=409,
            message="Insufficient stock to complete this operation",
            error="INSUFFICIENT_STOCK",
            details=details,
        )
