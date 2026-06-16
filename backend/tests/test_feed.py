"""Feed module tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.modules.auth.dependencies import get_current_user


@pytest.mark.asyncio
async def test_get_feed_unauthenticated():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/feed")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_feed_success_empty():
    mock_user = User(id="user-1", email="test@dev.local", handle="testuser", name="Test User")

    async def override_get_current_user():
        return mock_user

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=[]))
    )

    async def override_get_db():
        yield db_mock

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/feed")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_get_trending_cached():
    from unittest.mock import patch

    cached_data = '[{"id": "cs-1", "author": {"id": "u1", "handle": "test", "name": "Test", "avatar_url": null}, "title": "Cached Study", "slug": "cached-study", "summary": null, "ai_model": null, "visibility": "public", "tags": [], "likes_count": 5, "applause_count": 0, "aha_count": 0, "comments_count": 0, "published_at": null, "created_at": "2026-01-01T00:00:00Z"}]'

    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=cached_data)

    with patch(
        "app.modules.feed.router.get_redis_client",
        return_value=redis_mock,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/discover")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "Cached Study"