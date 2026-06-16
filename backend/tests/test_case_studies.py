"""Case studies module tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_create_case_study_unauthenticated():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/case-studies",
            json={"title": "Test Case Study"},
        )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_case_study_success():
    from app.db.models.case_study import CaseStudy
    from app.db.models.user import User
    from app.main import app
    from app.modules.auth.dependencies import get_current_user

    mock_user = User(
        id="user-1", email="test@dev.local", handle="testuser", name="Test User"
    )
    mock_cs = CaseStudy(
    id="cs-1",
    author_id="user-1",
    title="Test Case Study",
    slug="test-case-study",
    visibility="private",
    likes_count=0,
    applause_count=0,
    aha_count=0,
    comments_count=0,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
    )
    mock_cs.author = mock_user
    mock_cs.tags = []

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    with (
        patch(
            "app.modules.case_studies.service.create_case_study",
            new_callable=AsyncMock,
            return_value=mock_cs,
        ),
        patch(
            "app.modules.case_studies.service.get_current_version",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/case-studies",
                json={
                    "title": "Test Case Study",
                    "content": {"prompt": "test prompt", "final_output": "test output"},
                },
            )

    app.dependency_overrides.clear()
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_update_case_study_forbidden():
    from app.db.models.case_study import CaseStudy
    from app.db.models.user import User
    from app.modules.auth.dependencies import get_current_user

    mock_user = User(id="user-1", email="test@dev.local", handle="testuser", name="Test User")
    other_cs = CaseStudy(
        id="cs-1",
        author_id="other-user",
        title="Someone else's study",
        slug="someone-else",
        visibility="private",
    )

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    with patch(
        "app.modules.case_studies.service.get_case_study",
        new_callable=AsyncMock,
        return_value=other_cs,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/v1/case-studies/cs-1",
                json={"title": "Hacked title"},
            )

    app.dependency_overrides.clear()
    assert response.status_code == 403