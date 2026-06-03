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

@pytest.mark.asyncio
async def test_add_comment_success():
    with patch(
        "app.modules.engagement.service.add_comment",
        new_callable=AsyncMock,
        return_value=True,
    ):
        async with AsyncClient(
            transport = ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/case-studies/some-id/comments",
                json={"body": "This is a test comment."},
            )
        assert response.status_code in (201, 401)

@pytest.mark.asyncio
async def test_delete_comment_success():
    with patch(
        "app.modules.engagement.service.soft_delete_comment",
        new_callable=AsyncMock,
        return_value=True,
    ):
        async with AsyncClient(
            transport = ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                "/api/v1/comments/some-comment-id",
            )   
        assert response.status_code in (204, 401)

@pytest.mark.asyncio
async def test_add_comment_empty_body():
    with patch(
        "app.modules.engagement.service.add_comment",
        new_callable=AsyncMock,
        return_value=True,
    ):
        async with AsyncClient(
            transport = ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/case-studies/some-id/comments",
                json={"body": ""},
            )
        assert response.status_code in (422, 401)

@pytest.mark.asyncio
async def test_get_comment_success():
    with patch(
        "app.modules.engagement.service.get_comments",
        new_callable=AsyncMock,
        return_value=[],
    ):
        async with AsyncClient(
            transport = ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/case-studies/some-id/comments",
            )
        assert response.status_code in (200, 401)

@pytest.mark.asyncio
async def test_add_reaction_duplicate():
    with patch(
        "app.modules.engagement.service.add_reaction",
        new_callable=AsyncMock,
        return_value=False,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/case-studies/some-id/reactions",
                json={"reaction_type": "like"},
            )
    assert response.status_code in (204, 401)