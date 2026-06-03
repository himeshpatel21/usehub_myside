"""Case study CRUD and versioning logic."""

from datetime import UTC, datetime

from slugify import slugify
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import new_uuid
from app.db.models.case_study import CaseStudy, CaseStudyTag, CaseStudyVersion, Tag
from app.db.models.user import User
from app.db.redis import get_redis_client
from app.modules.case_studies.schemas import CaseStudyCreateIn, CaseStudyUpdateIn

STREAM_KEY = "stream:events"


async def _get_or_create_tags(db: AsyncSession, tag_names: list[str]) -> list[Tag]:
    tags = []
    for name in tag_names:
        slug = slugify(name, separator="-")
        result = await db.execute(select(Tag).where(Tag.slug == slug))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(id=new_uuid(), name=name, slug=slug)
            db.add(tag)
            await db.flush()
        tags.append(tag)
    return tags


async def _generate_slug(db: AsyncSession, title: str, author_id: str) -> str:
    base = slugify(title, max_length=100) or "case-study"
    slug = base
    counter = 1
    while True:
        result = await db.execute(
            select(CaseStudy).where(
                CaseStudy.author_id == author_id,
                CaseStudy.slug == slug,
            )
        )
        if not result.scalar_one_or_none():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


async def create_case_study(db: AsyncSession, author: User, data: CaseStudyCreateIn) -> CaseStudy:
    slug = await _generate_slug(db, data.title, author.id)
    case_study = CaseStudy(
        id=new_uuid(),
        author_id=author.id,
        title=data.title,
        slug=slug,
        summary=data.summary,
        ai_model=data.ai_model,
        ai_platform=data.ai_platform,
        visibility=data.visibility,
    )
    db.add(case_study)
    await db.flush()

    version = CaseStudyVersion(
        id=new_uuid(),
        case_study_id=case_study.id,
        version_number=1,
        content=data.content.model_dump(),
        change_message=data.change_message or "Initial version",
        created_at=datetime.now(UTC),
    )
    db.add(version)
    await db.flush()

    case_study.current_version_id = version.id

    tags = await _get_or_create_tags(db, data.tags)
    for tag in tags:
        db.add(CaseStudyTag(id=new_uuid(), case_study_id=case_study.id, tag_id=tag.id))

    if data.visibility == "public":
        case_study.published_at = datetime.now(UTC)
        await _emit_event(
            "case_study.published", {"case_study_id": case_study.id, "author_id": author.id}
        )

    await db.flush()
    return case_study


async def update_case_study(
    db: AsyncSession, case_study: CaseStudy, data: CaseStudyUpdateIn
) -> CaseStudy:
    if data.title is not None:
        case_study.title = data.title
    if data.summary is not None:
        case_study.summary = data.summary
    if data.ai_model is not None:
        case_study.ai_model = data.ai_model
    if data.ai_platform is not None:
        case_study.ai_platform = data.ai_platform

    was_private = case_study.visibility != "public"
    if data.visibility is not None:
        case_study.visibility = data.visibility
        if case_study.visibility == "public" and was_private:
            case_study.published_at = datetime.now(UTC)
            await _emit_event(
                "case_study.published",
                {"case_study_id": case_study.id, "author_id": case_study.author_id},
            )

    if data.content is not None:
        result = await db.execute(
            select(CaseStudyVersion)
            .where(CaseStudyVersion.case_study_id == case_study.id)
            .order_by(CaseStudyVersion.version_number.desc())
            .limit(1)
        )
        last = result.scalar_one()
        version = CaseStudyVersion(
            id=new_uuid(),
            case_study_id=case_study.id,
            version_number=last.version_number + 1,
            content=data.content.model_dump(),
            change_message=data.change_message or "Updated",
            created_at=datetime.now(UTC),
        )
        db.add(version)
        await db.flush()
        case_study.current_version_id = version.id

    if data.tags is not None:
        await db.execute(delete(CaseStudyTag).where(CaseStudyTag.case_study_id == case_study.id))
        tags = await _get_or_create_tags(db, data.tags)
        for tag in tags:
            db.add(CaseStudyTag(id=new_uuid(), case_study_id=case_study.id, tag_id=tag.id))

    await db.flush()
    return case_study


async def get_case_study(
    db: AsyncSession, case_study_id: str, viewer_id: str | None = None
) -> CaseStudy | None:
    result = await db.execute(
        select(CaseStudy)
        .where(CaseStudy.id == case_study_id, CaseStudy.deleted_at == None)  # noqa: E711
        .options(
            selectinload(CaseStudy.author),
            selectinload(CaseStudy.tags).selectinload(CaseStudyTag.tag),
        )
    )
    cs = result.scalar_one_or_none()
    if not cs:
        return None
    if cs.visibility == "private" and cs.author_id != viewer_id:
        return None
    return cs


async def get_current_version(db: AsyncSession, case_study: CaseStudy) -> CaseStudyVersion | None:
    if not case_study.current_version_id:
        return None
    result = await db.execute(
        select(CaseStudyVersion).where(CaseStudyVersion.id == case_study.current_version_id)
    )
    return result.scalar_one_or_none()


async def list_user_case_studies(
    db: AsyncSession,
    author_id: str,
    viewer_id: str | None,
    limit: int = 20,
    cursor: str | None = None,
) -> list[CaseStudy]:
    query = (
        select(CaseStudy)
        .where(
            CaseStudy.author_id == author_id,
            CaseStudy.deleted_at == None,  # noqa: E711
        )
        .options(
            selectinload(CaseStudy.author),
            selectinload(CaseStudy.tags).selectinload(CaseStudyTag.tag),
        )
        .order_by(CaseStudy.published_at.desc().nulls_last(), CaseStudy.created_at.desc())
        .limit(limit)
    )
    if viewer_id != author_id:
        query = query.where(CaseStudy.visibility == "public")
    if cursor:
        query = query.where(CaseStudy.id < cursor)

    result = await db.execute(query)
    return list(result.scalars())


async def list_public_case_studies(
    db: AsyncSession,
    limit: int = 20,
    cursor: str | None = None,
) -> list[CaseStudy]:
    query = (
        select(CaseStudy)
        .where(CaseStudy.visibility == "public", CaseStudy.deleted_at == None)  # noqa: E711
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
    return list(result.scalars())


async def soft_delete(db: AsyncSession, case_study: CaseStudy) -> None:
    case_study.deleted_at = datetime.now(UTC)
    await db.flush()


async def _emit_event(event_type: str, payload: dict) -> None:
    try:
        redis = get_redis_client()
        await redis.xadd(
            STREAM_KEY, {"type": event_type, **{str(k): str(v) for k, v in payload.items()}}
        )
    except Exception:
        pass  # Non-critical — events are best-effort
