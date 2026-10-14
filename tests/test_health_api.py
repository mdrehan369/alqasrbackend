from app.core.settings import get_settings
from app.db.session import get_db
from app.main import app
from app.utils.constants import HTTP_RESPONSE_MESSAGES

settings = get_settings()

LIVE_URL = "/health"
READY_URL = "/health/ready"


class _BrokenSession:
    async def execute(self, *args, **kwargs):
        raise RuntimeError("database is down")


async def _broken_db():
    yield _BrokenSession()


async def test_liveness_returns_healthy_envelope(unauth_client):
    response = await unauth_client.get(LIVE_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == HTTP_RESPONSE_MESSAGES.SUCCESS.value
    assert body["data"]["status"] == "healthy"
    assert body["data"]["version"] == settings.app_version
    assert body["data"]["checks"] == {}


async def test_liveness_requires_no_auth(unauth_client):
    response = await unauth_client.get(LIVE_URL)

    assert response.status_code == 200


async def test_readiness_reports_database_up(unauth_client):
    response = await unauth_client.get(READY_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == HTTP_RESPONSE_MESSAGES.SUCCESS.value
    assert body["data"]["status"] == "healthy"
    check = body["data"]["checks"]["database"]
    assert check["status"] == "up"
    assert check["latency_ms"] is not None


async def test_readiness_returns_503_when_database_down(unauth_client):
    original = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = _broken_db
    try:
        response = await unauth_client.get(READY_URL)
    finally:
        app.dependency_overrides[get_db] = original

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["message"] == HTTP_RESPONSE_MESSAGES.SERVICE_UNAVAILABLE.value
    assert body["data"]["status"] == "unhealthy"
    assert body["data"]["checks"]["database"]["status"] == "down"


async def test_readiness_requires_no_auth(unauth_client):
    response = await unauth_client.get(READY_URL)

    assert response.status_code == 200


async def test_health_routes_are_not_under_admin_prefix(unauth_client):
    response = await unauth_client.get("/api/v1/admin/health")

    assert response.status_code == 404
