from datetime import datetime

from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.auth import create_access_token, decode_access_token
from app.core.exceptions import BadRequestError, UnauthorizedAccessError
from app.core.settings import get_settings
from app.schemas.auth import AccessTokenData, SigninRequest, SigninResponse, TokenType

settings = get_settings()


async def signin_service(payload: SigninRequest):

    if payload.email != settings.admin_email:
        raise BadRequestError("Invalid email address")

    if payload.password != settings.admin_password.get_secret_value():
        raise BadRequestError("Invalid password")

    data = {"email": payload.email, "logged_in_at": str(datetime.now())}

    access_token = create_access_token(data)

    return SigninResponse(access_token=access_token, token_type=TokenType.BEARER)


async def get_current_user_service(access_token: str):
    if access_token is None:
        raise UnauthorizedAccessError("Authorization header is missing")
    try:
        payload = decode_access_token(access_token)
        email: str | None = payload.get("email")
        logged_in_at: datetime | None = payload.get("logged_in_at")
        if email is None or logged_in_at is None:
            raise UnauthorizedAccessError("Invalid token")
        return AccessTokenData(email=email, logged_in_at=logged_in_at)

    except ExpiredSignatureError:
        raise UnauthorizedAccessError("Access token has expired")

    except InvalidTokenError:
        raise UnauthorizedAccessError("Invalid token")
