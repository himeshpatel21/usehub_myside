"""Reactions, comments, and bookmarks."""

from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import new_uuid
from app.db.models.engagement import Bookmark, Comment, Reaction
from app.db.redis import get_redis_client

STREAM_KEY = "stream:events"

REACTION_COLUMN = {
    "like": "likes_count",
    "applause": "applause_count",
    "aha": "aha_count",
}


async def add_reaction(
    db: AsyncSession, user_id: str, case_study_id: str, reaction_type: str
) -> bool:
    """
    Idempotent. Returns True if newly created.
    Uses ON CONFLICT DO NOTHING to avoid duplicate reactions.
    Counter update is a single atomic SQL statement — no read-modify-write.
    """
    column = REACTION_COLUMN[reaction_type]
    stmt = (
        pg_insert(Reaction)
        .values(
            id=new_uuid(),
            user_id=user_id,
            target_type="case_study",
            target_id=case_study_id,
            reaction_type=reaction_type,
        )
        .on_conflict_do_nothing(constraint="uq_reaction")
        .returning(Reaction.id)
    )
    result = await db.execute(stmt)
    inserted = result.scalar_one_or_none()
    if not inserted:
        return False

    await db.execute(
        text(f"UPDATE case_studies SET {column} = {column} + 1 WHERE id = :id"),
        {"id": case_study_id},
    )

    await _emit_event(
        "reaction.created",
        {
            "user_id": user_id,
            "case_study_id": case_study_id,
            "reaction_type": reaction_type,
        },
    )
    return True


async def remove_reaction(
    db: AsyncSession, user_id: str, case_study_id: str, reaction_type: str
) -> bool:
    column = REACTION_COLUMN[reaction_type]
    result = await db.execute(
        select(Reaction).where(
            Reaction.user_id == user_id,
            Reaction.target_type == "case_study",
            Reaction.target_id == case_study_id,
            Reaction.reaction_type == reaction_type,
        )
    )
    reaction = result.scalar_one_or_none()
    if not reaction:
        return False

    await db.delete(reaction)
    await db.execute(
        text(f"UPDATE case_studies SET {column} = GREATEST({column} - 1, 0) WHERE id = :id"),
        {"id": case_study_id},
    )
    return True


async def get_reaction_counts(db: AsyncSession, case_study_id: str, user_id: str | None) -> dict:
    from app.db.models.case_study import CaseStudy

    result = await db.execute(
        select(
            CaseStudy.likes_count,
            CaseStudy.applause_count,
            CaseStudy.aha_count,
        ).where(CaseStudy.id == case_study_id)
    )
    row = result.one_or_none()
    if not row:
        return {"likes_count": 0, "applause_count": 0, "aha_count": 0, "user_reactions": []}

    user_reactions: list[str] = []
    if user_id:
        result = await db.execute(
            select(Reaction.reaction_type).where(
                Reaction.user_id == user_id,
                Reaction.target_type == "case_study",
                Reaction.target_id == case_study_id,
            )
        )
        user_reactions = list(result.scalars())

    return {
        "likes_count": row.likes_count,
        "applause_count": row.applause_count,
        "aha_count": row.aha_count,
        "user_reactions": user_reactions,
    }


async def add_comment(
    db: AsyncSession,
    user_id: str,
    case_study_id: str,
    body: str,
    parent_id: str | None = None,
) -> Comment:
    comment = Comment(
        id=new_uuid(),
        case_study_id=case_study_id,
        user_id=user_id,
        body=body,
        parent_id=parent_id,
    )
    db.add(comment)
    await db.execute(
        text("UPDATE case_studies SET comments_count = comments_count + 1 WHERE id = :id"),
        {"id": case_study_id},
    )
    await db.flush()

    await _emit_event(
        "comment.created",
        {"user_id": user_id, "case_study_id": case_study_id, "comment_id": comment.id},
    )
    return comment


async def get_comments(
    db: AsyncSession,
    case_study_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[Comment]:
    result = await db.execute(
        select(Comment)
        .where(Comment.case_study_id == case_study_id)
        .options(selectinload(Comment.user))
        .order_by(Comment.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars())


async def soft_delete_comment(db: AsyncSession, comment: Comment) -> None:
    comment.deleted_at = datetime.now(UTC)
    comment.body = "[deleted]"
    await db.execute(
        text(
            "UPDATE case_studies SET comments_count = GREATEST(comments_count - 1, 0) WHERE id = :id"
        ),
        {"id": comment.case_study_id},
    )
    await db.flush()


async def get_comment(db: AsyncSession, comment_id: str) -> Comment | None:
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id).options(selectinload(Comment.user))
    )
    return result.scalar_one_or_none()


async def toggle_bookmark(db: AsyncSession, user_id: str, case_study_id: str) -> bool:
    """Returns True if bookmarked, False if removed."""
    result = await db.execute(
        select(Bookmark).where(Bookmark.user_id == user_id, Bookmark.case_study_id == case_study_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        return False
    else:
        db.add(Bookmark(id=new_uuid(), user_id=user_id, case_study_id=case_study_id))
        await db.flush()
        return True


async def get_user_bookmarks(
    db: AsyncSession, user_id: str, limit: int = 20, offset: int = 0
) -> list[str]:
    result = await db.execute(
        select(Bookmark.case_study_id)
        .where(Bookmark.user_id == user_id)
        .order_by(Bookmark.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars())


async def _emit_event(event_type: str, payload: dict) -> None:
    try:
        redis = get_redis_client()
        await redis.xadd(
            STREAM_KEY,
            {"type": event_type, **{str(k): str(v) for k, v in payload.items()}},
        )
    except Exception:
        pass
