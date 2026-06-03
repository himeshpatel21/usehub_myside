from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification
from app.db.models.user import User
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    type: str
    payload: dict
    read_at: datetime | None
    created_at: datetime


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationOut]:
    result = await db.execute(
        select(Notification)
        .where(Notification.recipient_id == current_user.id)
        .order_by(Notification.read_at.asc().nulls_first(), Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    notifications = list(result.scalars())
    return [
        NotificationOut(
            id=n.id,
            type=n.type,
            payload=n.payload,
            read_at=n.read_at,
            created_at=n.created_at,
        )
        for n in notifications
    ]


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    from sqlalchemy import func, select

    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.recipient_id == current_user.id,
            Notification.read_at == None,  # noqa: E711
        )
    )
    count = result.scalar_one()
    return {"count": count}


@router.post("/mark-read", status_code=204)
async def mark_read(
    ids: list[str] | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    now = datetime.now(UTC)
    stmt = update(Notification).where(
        Notification.recipient_id == current_user.id,
        Notification.read_at == None,  # noqa: E711
    )
    if ids:
        stmt = stmt.where(Notification.id.in_(ids))
    stmt = stmt.values(read_at=now)
    await db.execute(stmt)
