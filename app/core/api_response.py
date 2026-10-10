from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.utils.constants import HTTP_RESPONSE_MESSAGES

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = Field(default=True, description="Whether the request succeeded.")
    message: str = Field(
        default=HTTP_RESPONSE_MESSAGES.SUCCESS.value,
        description="Human-readable result message.",
    )
    data: T | None = Field(default=None, description="Response payload.")


class ErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Human-readable error message.")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Always false for errors.")
    error: ErrorDetail = Field(description="Error details.")
