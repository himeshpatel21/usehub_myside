from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_user
from app.modules.engagement import service
from app.modules.engagement.schemas import (
    CommentAuthorOut,
    CommentIn,
    CommentOut,
    ReactionCountsOut,
    ReactionIn,
)

router = APIRouter(tags=["engagement"])


# ── Reactions ──────────────────────────────────────────────────────────────────


@router.post(
    "/case-studies/{case_study_id}/reactions",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_reaction(
    case_study_id: str,
    data: ReactionIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.add_reaction(db, current_user.id, case_study_id, data.reaction_type)


@router.delete(
    "/case-studies/{case_study_id}/reactions/{reaction_type}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_reaction(
    case_study_id: str,
    reaction_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if reaction_type not in ("like", "applause", "aha"):
        raise HTTPException(status_code=400, detail="Invalid reaction type")
    await service.remove_reaction(db, current_user.id, case_study_id, reaction_type)


@router.get(
    "/case-studies/{case_study_id}/reactions",
    response_model=ReactionCountsOut,
)
async def get_reactions(
    case_study_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> ReactionCountsOut:
    data = await service.get_reaction_counts(
        db, case_study_id, current_user.id if current_user else None
    )
    return ReactionCountsOut(**data)


# ── Comments ──────────────────────────────────────────────────────────────────


@router.post(
    "/case-studies/{case_study_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    case_study_id: str,
    data: CommentIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentOut:
    comment = await service.add_comment(
        db, current_user.id, case_study_id, data.body, data.parent_id
    )
    return CommentOut(
        id=comment.id,
        author=CommentAuthorOut(
            id=current_user.id,
            handle=current_user.handle,
            name=current_user.name,
            avatar_url=current_user.avatar_url,
        ),
        body=comment.body,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
    )


@router.get("/case-studies/{case_study_id}/comments", response_model=list[CommentOut])
async def get_comments(
    case_study_id: str,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[CommentOut]:
    comments = await service.get_comments(db, case_study_id, limit, offset)
    return [
        CommentOut(
            id=c.id,
            author=CommentAuthorOut(
                id=c.user.id,
                handle=c.user.handle,
                name=c.user.name,
                avatar_url=c.user.avatar_url,
            ),
            body=c.body,
            parent_id=c.parent_id,
            created_at=c.created_at,
            deleted_at=c.deleted_at,
        )
        for c in comments
    ]


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    comment = await service.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await service.soft_delete_comment(db, comment)


# ── Bookmarks ─────────────────────────────────────────────────────────────────


@router.post(
    "/case-studies/{case_study_id}/bookmarks",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def toggle_bookmark(
    case_study_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.toggle_bookmark(db, current_user.id, case_study_id)


@router.delete(
    "/case-studies/{case_study_id}/bookmarks",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_bookmark(
    case_study_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.toggle_bookmark(db, current_user.id, case_study_id)
