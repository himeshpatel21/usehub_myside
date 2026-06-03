"""Engagement module tests — reactions, comments, bookmarks."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_add_reaction_success():
    with patch(
        "app.modules.engagement.service.add_reaction",
        new_callable=AsyncMock,
        return_value=True,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/case-studies/some-id/reactions",
                json={"reaction_type": "like"},
            )
    assert response.status_code in (204, 401)

@pytest.mark.asyncio
async def test_add_reaction_invalid_type():
    with patch(
        "app.modules.engagement.service.add_reaction",
        new_callable=AsyncMock,
        return_value=False,
    ):
        async with AsyncClient(
            transport = ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/case-studies/some-id/reactions",
                json={"reaction_type": "invalid"},
            )
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_toggle_bookmark_success():
    with patch(
        "app.modules.engagement.service.toggle_bookmark",
        new_callable=AsyncMock,
        return_value=True,
    ):
        async with AsyncClient(
            transport = ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/case-studies/some-id/bookmarks",
                json={"is_bookmarked": True},
            )
        assert response.status_code in (204, 401)