from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr


class TokenType(Enum):
    BEARER = "bearer"


class SigninRequest(BaseModel):
    email: EmailStr
    password: str


class SigninResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: TokenType


class AccessTokenData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    logged_in_at: datetime
