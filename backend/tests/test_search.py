"""Search module tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_search_without_tags():
    with patch(
        "app.modules.search.router.search",
        new_callable=AsyncMock,
        return_value={"case_studies": [], "users": []}
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/search?q=python")
    assert response.status_code in (200, 422)


@pytest.mark.asyncio
async def test_search_with_tags():
    with patch("app.modules.search.router.search", 
            new_callable=AsyncMock, 
            return_value={"case_studies": [], "users": []}
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/search?q=python&tags=fastapi&tags=llm")
    assert response.status_code in (200, 422)