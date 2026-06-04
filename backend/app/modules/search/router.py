"""
Postgres full-text search over case studies and users.
GIN index on the tsvector column is created via migration.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.case_study import CaseStudy, CaseStudyTag
from app.db.models.user import User
from app.db.session import get_db
from app.modules.case_studies.router import _cs_to_list_out
from app.modules.users.schemas import UserMinimalOut
from app.db.models.case_study import CaseStudy, CaseStudyTag, Tag

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query(..., min_length=1, max_length=200),
    type: str = Query(default="case_study", description="case_study | user | all"),
    tags: list[str] = Query(default=[]),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if type not in ("case_study", "user", "all"):
        raise HTTPException(status_code=400, detail="type must be case_study, user, or all")

    results: dict = {}

    if type in ("case_study", "all"):
        cs_result = await db.execute(
            select(CaseStudy)
            .where(
                CaseStudy.visibility == "public",
                CaseStudy.deleted_at == None,  # noqa: E711
                text(
                    "to_tsvector('english', case_studies.title || ' ' || "
                    "COALESCE(case_studies.summary, '')) @@ plainto_tsquery('english', :q)"
                ),
            )
            .options(
                selectinload(CaseStudy.author),
                selectinload(CaseStudy.tags).selectinload(CaseStudyTag.tag),
            )
            .order_by(
                text(
                    "ts_rank(to_tsvector('english', case_studies.title || ' ' || "
                    "COALESCE(case_studies.summary, '')), plainto_tsquery('english', :q)) DESC"
                )
            )
            .where(
                *( 
                    [CaseStudy.tags.any(CaseStudyTag.tag.has(Tag.slug.in_(tags)))]
                    if tags else []
                )
            )
            .limit(limit)
            .offset(offset)
            .params(q=q)
        )
        case_studies = list(cs_result.scalars())
        results["case_studies"] = [_cs_to_list_out(cs) for cs in case_studies]

    if type in ("user", "all"):
        user_result = await db.execute(
            select(User)
            .where(
                User.is_active == True,  # noqa: E712
                text(
                    "to_tsvector('english', users.name || ' ' || users.handle) "
                    "@@ plainto_tsquery('english', :q)"
                ),
            )
            .limit(limit)
            .offset(offset)
            .params(q=q)
        )
        users = list(user_result.scalars())
        results["users"] = [
            UserMinimalOut(id=u.id, handle=u.handle, name=u.name, avatar_url=u.avatar_url)
            for u in users
        ]

    return results
