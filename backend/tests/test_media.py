"""Media module tests."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models.user import User
from app.main import app
from app.modules.auth.dependencies import get_current_user


@pytest.mark.asyncio
async def test_avatar_upload_url_unauthenticated():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/media/avatar-upload-url")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_avatar_upload_url_success():
    mock_user = User(id="user-1", email="test@dev.local", handle="testuser", name="Test User")

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    s3_mock = MagicMock()
    s3_mock.generate_presigned_url.return_value = "https://fake-s3-url.com/upload"

    with patch(
        "app.modules.media.router._get_s3",
        return_value=s3_mock,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/media/avatar-upload-url",
                params={"content_type": "image/jpeg"},
            )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "key" in response.json()


@pytest.mark.asyncio
async def test_avatar_upload_url_invalid_content_type():
    mock_user = User(id="user-1", email="test@dev.local", handle="testuser", name="Test User")

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/media/avatar-upload-url",
            params={"content_type": "application/pdf"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400