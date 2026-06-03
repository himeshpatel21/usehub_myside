from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case_study import CaseStudy
from app.db.models.user import User
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_user
from app.modules.case_studies import service
from app.modules.case_studies.schemas import (
    AuthorOut,
    CaseStudyCreateIn,
    CaseStudyListOut,
    CaseStudyOut,
    CaseStudyUpdateIn,
    TagOut,
)

router = APIRouter(prefix="/case-studies", tags=["case-studies"])


def _cs_to_list_out(cs: CaseStudy) -> CaseStudyListOut:
    return CaseStudyListOut(
        id=cs.id,
        author=AuthorOut(
            id=cs.author.id,
            handle=cs.author.handle,
            name=cs.author.name,
            avatar_url=cs.author.avatar_url,
        ),
        title=cs.title,
        slug=cs.slug,
        summary=cs.summary,
        ai_model=cs.ai_model,
        visibility=cs.visibility,
        tags=[TagOut(id=t.tag.id, name=t.tag.name, slug=t.tag.slug) for t in (cs.tags or [])],
        likes_count=cs.likes_count,
        applause_count=cs.applause_count,
        aha_count=cs.aha_count,
        comments_count=cs.comments_count,
        published_at=cs.published_at,
        created_at=cs.created_at,
    )


async def _cs_to_full_out(cs: CaseStudy, db: AsyncSession) -> CaseStudyOut:
    version = await service.get_current_version(db, cs)
    return CaseStudyOut(
        id=cs.id,
        author=AuthorOut(
            id=cs.author.id,
            handle=cs.author.handle,
            name=cs.author.name,
            avatar_url=cs.author.avatar_url,
        ),
        title=cs.title,
        slug=cs.slug,
        summary=cs.summary,
        ai_model=cs.ai_model,
        ai_platform=cs.ai_platform,
        visibility=cs.visibility,
        content=version.content if version else None,
        tags=[TagOut(id=t.tag.id, name=t.tag.name, slug=t.tag.slug) for t in (cs.tags or [])],
        likes_count=cs.likes_count,
        applause_count=cs.applause_count,
        aha_count=cs.aha_count,
        comments_count=cs.comments_count,
        current_version_id=cs.current_version_id,
        published_at=cs.published_at,
        created_at=cs.created_at,
        updated_at=cs.updated_at,
    )


@router.post("", response_model=CaseStudyOut, status_code=status.HTTP_201_CREATED)
async def create_case_study(
    data: CaseStudyCreateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseStudyOut:
    cs = await service.create_case_study(db, current_user, data)
    return await _cs_to_full_out(cs, db)


@router.get("", response_model=list[CaseStudyListOut])
async def list_public(
    limit: int = Query(default=20, le=100),
    cursor: str | None = Query(default=None),
) -> list[CaseStudyListOut]:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        items = await service.list_public_case_studies(db, limit, cursor)
    return [_cs_to_list_out(cs) for cs in items]


@router.get("/{case_study_id}", response_model=CaseStudyOut)
async def get_case_study(
    case_study_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> CaseStudyOut:
    cs = await service.get_case_study(
        db, case_study_id, viewer_id=current_user.id if current_user else None
    )
    if not cs:
        raise HTTPException(status_code=404, detail="Case study not found")
    return await _cs_to_full_out(cs, db)


@router.patch("/{case_study_id}", response_model=CaseStudyOut)
async def update_case_study(
    case_study_id: str,
    data: CaseStudyUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseStudyOut:
    cs = await service.get_case_study(db, case_study_id, viewer_id=current_user.id)
    if not cs:
        raise HTTPException(status_code=404, detail="Case study not found")
    if cs.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    cs = await service.update_case_study(db, cs, data)
    return await _cs_to_full_out(cs, db)


@router.post("/{case_study_id}/publish", response_model=CaseStudyOut)
async def publish_case_study(
    case_study_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseStudyOut:
    cs = await service.get_case_study(db, case_study_id, viewer_id=current_user.id)
    if not cs:
        raise HTTPException(status_code=404, detail="Case study not found")
    if cs.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    update_data = CaseStudyUpdateIn(visibility="public")
    cs = await service.update_case_study(db, cs, update_data)
    return await _cs_to_full_out(cs, db)


@router.delete("/{case_study_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_study(
    case_study_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    cs = await service.get_case_study(db, case_study_id, viewer_id=current_user.id)
    if not cs:
        raise HTTPException(status_code=404, detail="Case study not found")
    if cs.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await service.soft_delete(db, cs)
