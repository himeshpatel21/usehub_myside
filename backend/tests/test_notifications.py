"""Notifications module tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.modules.auth.dependencies import get_current_user


@pytest.mark.asyncio
async def test_list_notifications_unauthenticated():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/notifications")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unread_count_success():
    mock_user = User(id="user-1", email="test@dev.local", handle="testuser", name="Test User")

    async def override_get_current_user():
        return mock_user

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(
        return_value=MagicMock(scalar_one=MagicMock(return_value=3))
    )

    async def override_get_db():
        yield db_mock

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/notifications/unread-count")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["count"] == 3
@pytest.mark.asyncio
async def test_mark_read_success():
    mock_user = User(id="user-1", email="test@dev.local", handle="testuser", name="Test User")

    async def override_get_current_user():
        return mock_user

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=MagicMock())

    async def override_get_db():
        yield db_mock

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/notifications/mark-read", json=[])

    app.dependency_overrides.clear()
    assert response.status_code == 204