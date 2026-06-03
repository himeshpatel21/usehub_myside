"""Dev login endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models.user import User
from app.main import app

MOCK_USER = User(
    id="00000000-0000-0000-0000-000000000001",
    email="max@dev.local",
    handle="max",
    name="Max",
)


@pytest.mark.asyncio
async def test_dev_login_success():
    with (
        patch(
            "app.modules.auth.router.get_or_create_dev_user",
            new_callable=AsyncMock,
            return_value=MOCK_USER,
        ),
        patch(
            "app.modules.auth.router.create_session",
            new_callable=AsyncMock,
            return_value="test-session-id",
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/auth/login/email",
                json={"username": "max", "password": "mustermann"},
            )
    assert response.status_code == 200
    assert response.json()["handle"] == "max"
    assert response.cookies.get("usehub_session") == "test-session-id"


@pytest.mark.asyncio
async def test_dev_login_invalid_credentials():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login/email",
            json={"username": "max", "password": "wrong"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_route_not_oauth_provider():
    """GET /auth/me must not be captured by GET /auth/{provider}."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

