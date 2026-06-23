from typing import Any, Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    success: bool = False
    status_code: int = 500
    message: str = "An error occurred"
    error: Optional[str] = None
    details: Optional[Any] = None

    @classmethod
    def from_exception(cls, exc: Exception) -> "ErrorResponse":
        """
        Build an ErrorResponse from any AppException (or subclass).
        Uses getattr so it also handles unexpected exceptions gracefully.
        """
        return cls(
            success=False,
            status_code=getattr(exc, "status_code", 500),
            message=getattr(exc, "message", str(exc)),
            error=getattr(exc, "error", "INTERNAL_ERROR"),
            details=getattr(exc, "details", None),
        )

    @classmethod
    def internal_error(cls, message: str = "Internal server error") -> "ErrorResponse":
        return cls(success=False, status_code=500, message=message, error="INTERNAL_ERROR")
