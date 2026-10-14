from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.settings import get_settings
from app.db import models as _models  # noqa: F401  registers models
from app.db.base import Base
from app.db.session import get_db
from app.main import app

settings = get_settings()

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
AUTH_URL = "/api/v1/admin/auth/"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            AUTH_URL,
            json={
                "email": str(settings.admin_email),
                "password": settings.admin_password.get_secret_value(),
            },
        )
        assert response.status_code == 200, response.text
        ac.headers["Authorization"] = (
            f"Bearer {response.json()['data']['access_token']}"
        )

        yield ac

    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def unauth_client(client):  # noqa: ARG001  ensures tables + overrides are ready
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session(client):  # noqa: ARG001  ensures tables exist first
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def fake_imagekit(monkeypatch):
    counter = {"n": 0}

    async def upload(**kwargs):
        counter["n"] += 1
        n = counter["n"]
        return SimpleNamespace(
            file_id=f"file-{n}",
            url=f"https://ik.example.com/{n}.png",
            file_path=f"/products/{n}.png",
        )

    files = SimpleNamespace(upload=AsyncMock(side_effect=upload), delete=AsyncMock())
    client = SimpleNamespace(files=files)

    monkeypatch.setattr("app.services.image.imagekit_client", client)

    return client
