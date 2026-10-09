from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from app.utils.constants import HTTP_RESPONSE_MESSAGES

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = HTTP_RESPONSE_MESSAGES.SUCCESS.value
    data: T | None
