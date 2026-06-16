"""Users module tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models.user import User
from app.main import app
from app.modules.auth.dependencies import get_current_user


@pytest.mark.asyncio
async def test_get_me_unauthenticated():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_success():
    mock_user = User(
    id="user-1",
    email="test@dev.local",
    handle="testuser",
    name="Test User",
    followers_count=0,
    following_count=0,
    )

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/users/me")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["handle"] == "testuser"