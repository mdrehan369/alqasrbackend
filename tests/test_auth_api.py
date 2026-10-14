from datetime import datetime, timedelta

import jwt

from app.core.auth import create_access_token
from app.core.settings import get_settings
from app.utils.constants import HTTP_RESPONSE_MESSAGES, JWT_ALGORITHM

settings = get_settings()

AUTH_URL = "/api/v1/admin/auth/"
ME_URL = "/api/v1/admin/auth/me"
CATEGORY_URL = "/api/v1/admin/categories/"


def _credentials() -> dict[str, str]:
    return {
        "email": str(settings.admin_email),
        "password": settings.admin_password.get_secret_value(),
    }


async def _signin(client) -> str:
    response = await client.post(AUTH_URL, json=_credentials())
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _claims() -> dict[str, str]:
    return {
        "email": str(settings.admin_email),
        "logged_in_at": str(datetime.now()),
    }


async def test_signin_success_returns_bearer_token(unauth_client):
    response = await unauth_client.post(AUTH_URL, json=_credentials())

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == HTTP_RESPONSE_MESSAGES.SUCCESS.value
    assert body["data"]["token_type"] == "bearer"
    assert isinstance(body["data"]["access_token"], str)
    assert body["data"]["access_token"]


async def test_signin_rejects_unknown_email(unauth_client):
    payload = _credentials() | {"email": "someone.else@example.com"}

    response = await unauth_client.post(AUTH_URL, json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.BAD_REQUEST.value
    assert body["error"]["message"] == "Invalid email address"


async def test_signin_rejects_wrong_password(unauth_client):
    payload = _credentials() | {"password": "not-the-password"}

    response = await unauth_client.post(AUTH_URL, json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.BAD_REQUEST.value
    assert body["error"]["message"] == "Invalid password"


async def test_signin_rejects_invalid_email_format(unauth_client):
    response = await unauth_client.post(
        AUTH_URL, json={"email": "not-an-email", "password": "whatever"}
    )

    assert response.status_code == 422


async def test_signin_rejects_missing_fields(unauth_client):
    response = await unauth_client.post(AUTH_URL, json={})

    assert response.status_code == 422


async def test_get_me_returns_token_claims(unauth_client):
    token = await _signin(unauth_client)

    response = await unauth_client.get(ME_URL, headers=_bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == HTTP_RESPONSE_MESSAGES.SUCCESS.value
    assert body["data"]["email"] == str(settings.admin_email)
    assert body["data"]["logged_in_at"] is not None


async def test_get_me_without_token_returns_401(unauth_client):
    response = await unauth_client.get(ME_URL)

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.UNAUTHORIZED.value
    assert body["error"]["message"] == "Authorization header is missing"


async def test_get_me_with_invalid_token_returns_401(unauth_client):
    response = await unauth_client.get(ME_URL, headers=_bearer("not-a-token"))

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.UNAUTHORIZED.value
    assert body["error"]["message"] == "Invalid token"


async def test_get_me_with_expired_token_returns_401(unauth_client):
    token = create_access_token(_claims(), timedelta(seconds=-1))

    response = await unauth_client.get(ME_URL, headers=_bearer(token))

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.UNAUTHORIZED.value
    assert body["error"]["message"] == "Access token has expired"


async def test_get_me_with_token_missing_claims_returns_401(unauth_client):
    token = create_access_token({"unexpected": "claim"})

    response = await unauth_client.get(ME_URL, headers=_bearer(token))

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.UNAUTHORIZED.value
    assert body["error"]["message"] == "Invalid token"


async def test_get_me_with_wrong_secret_returns_401(unauth_client):
    token = jwt.encode(_claims(), "a-totally-different-secret", algorithm=JWT_ALGORITHM)

    response = await unauth_client.get(ME_URL, headers=_bearer(token))

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.UNAUTHORIZED.value
    assert body["error"]["message"] == "Invalid token"


async def test_get_me_with_non_bearer_scheme_returns_401(unauth_client):
    response = await unauth_client.get(
        ME_URL, headers={"Authorization": "Basic YWRtaW46cGFzcw=="}
    )

    assert response.status_code == 401


async def test_get_me_with_empty_bearer_token_returns_401(unauth_client):
    response = await unauth_client.get(ME_URL, headers={"Authorization": "Bearer "})

    assert response.status_code == 401


async def test_protected_route_without_token_returns_401(unauth_client):
    response = await unauth_client.get(CATEGORY_URL)

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.UNAUTHORIZED.value


async def test_protected_route_with_invalid_token_returns_401(unauth_client):
    response = await unauth_client.get(CATEGORY_URL, headers=_bearer("bad-token"))

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == HTTP_RESPONSE_MESSAGES.UNAUTHORIZED.value


async def test_signin_token_grants_access_to_protected_route(unauth_client):
    token = await _signin(unauth_client)

    response = await unauth_client.post(
        CATEGORY_URL, json={"name": "auth-granted"}, headers=_bearer(token)
    )

    assert response.status_code == 201
    assert response.json()["data"]["name"] == "auth-granted"


async def test_authenticated_client_fixture_reaches_protected_route(client):
    response = await client.get(CATEGORY_URL)

    assert response.status_code == 200
    assert response.json()["success"] is True
