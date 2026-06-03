"""FastAPI dependencies for authentication."""

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.user import User
from app.db.redis import get_redis_client
from app.db.session import get_db
from app.modules.auth.session import get_session

settings = get_settings()


async def get_current_user(
    session_token: str | None = Cookie(default=None, alias="usehub_session"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    redis = get_redis_client()
    session_data = await get_session(redis, session_token)
    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user_id = session_data.get("user_id")
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def get_optional_user(
    session_token: str | None = Cookie(default=None, alias="usehub_session"),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not session_token:
        return None
    try:
        return await get_current_user(session_token=session_token, db=db)
    except HTTPException:
        return None
