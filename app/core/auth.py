from datetime import UTC, datetime, timedelta

import jwt

from app.core.settings import get_settings
from app.utils.constants import JWT_ALGORITHM

settings = get_settings()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, settings.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM
    )


def decode_access_token(access_token: str):
    return jwt.decode(
        access_token, settings.jwt_secret.get_secret_value(), algorithms=[JWT_ALGORITHM]
    )
