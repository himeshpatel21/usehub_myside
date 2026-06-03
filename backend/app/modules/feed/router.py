"""
Feed module — Postgres-based cursor-paginated feed for v1.
Redis fan-out is intentionally deferred until measurements demand it.
"""

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.case_study import CaseStudy, CaseStudyTag
from app.db.models.social import Follow
from app.db.models.user import User
from app.db.redis import get_redis_client
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.case_studies.router import _cs_to_list_out
from app.modules.case_studies.schemas import CaseStudyListOut

router = APIRouter(tags=["feed"])

TRENDING_CACHE_KEY = "feed:trending"
TRENDING_TTL = 600  # 10 minutes


@router.get("/feed", response_model=list[CaseStudyListOut])
async def get_feed(
    limit: int = Query(default=20, le=100),
    cursor: str | None = Query(default=None, description="ISO datetime cursor for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CaseStudyListOut]:
    """
    Home feed: case studies from users the current user follows.
    Cursor-paginated by published_at DESC.
    """
    query = (
        select(CaseStudy)
        .join(Follow, Follow.followee_id == CaseStudy.author_id)
        .where(
            Follow.follower_id == current_user.id,
            CaseStudy.visibility == "public",
            CaseStudy.deleted_at == None,  # noqa: E711
        )
        .options(
            selectinload(CaseStudy.author),
            selectinload(CaseStudy.tags).selectinload(CaseStudyTag.tag),
        )
        .order_by(CaseStudy.published_at.desc())
        .limit(limit)
    )

    if cursor:
        query = query.where(CaseStudy.published_at < cursor)

    result = await db.execute(query)
    items = list(result.scalars())
    return [_cs_to_list_out(cs) for cs in items]


@router.get("/discover", response_model=list[CaseStudyListOut])
async def get_trending(
    limit: int = Query(default=20, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[CaseStudyListOut]:
    """
    Trending discovery feed — cached in Redis for 10 minutes.
    Scores: likes + applause + aha + (comments * 2), within the last 7 days.
    """
    redis = get_redis_client()
    cached = await redis.get(TRENDING_CACHE_KEY)
    if cached:
        data = json.loads(cached)
        return [CaseStudyListOut(**item) for item in data[:limit]]

    result = await db.execute(
        select(CaseStudy)
        .where(
            CaseStudy.visibility == "public",
            CaseStudy.deleted_at == None,  # noqa: E711
            text("case_studies.published_at > NOW() - INTERVAL '7 days'"),
        )
        .options(
            selectinload(CaseStudy.author),
            selectinload(CaseStudy.tags).selectinload(CaseStudyTag.tag),
        )
        .order_by(
            text(
                "(case_studies.likes_count + case_studies.applause_count + "
                "case_studies.aha_count + case_studies.comments_count * 2) DESC"
            )
        )
        .limit(50)
    )
    items = list(result.scalars())
    out = [_cs_to_list_out(cs) for cs in items]

    # Cache serialized result
    serialized = json.dumps([item.model_dump(mode="json") for item in out])
    await redis.setex(TRENDING_CACHE_KEY, TRENDING_TTL, serialized)

    return out[:limit]
