from typing import Any, Optional
from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 200
    message: str = "Success"
    data: Optional[Any] = None

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def ok(
        cls,
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
    ) -> "SuccessResponse":
        return cls(success=True, status_code=status_code, message=message, data=data)

    @classmethod
    def created(
        cls,
        data: Any = None,
        message: str = "Created successfully",
    ) -> "SuccessResponse":
        return cls(success=True, status_code=201, message=message, data=data)
