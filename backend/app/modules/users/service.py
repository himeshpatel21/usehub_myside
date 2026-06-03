"""User profile and social graph business logic."""

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import new_uuid
from app.db.models.profile import Profile, UserTool
from app.db.models.social import Block, Follow
from app.db.models.user import User
from app.modules.users.schemas import ProfileUpdateIn


async def get_user_by_handle(db: AsyncSession, handle: str) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.handle == handle, User.is_active == True)  # noqa: E712
        .options(
            selectinload(User.profile).selectinload(Profile.tools).selectinload(UserTool.tool),
            selectinload(User.profile).selectinload(Profile.projects),
        )
    )
    return result.scalar_one_or_none()


async def is_following(db: AsyncSession, follower_id: str, followee_id: str) -> bool:
    result = await db.execute(
        select(Follow).where(Follow.follower_id == follower_id, Follow.followee_id == followee_id)
    )
    return result.scalar_one_or_none() is not None


async def is_blocked(db: AsyncSession, viewer_id: str, target_id: str) -> bool:
    result = await db.execute(
        select(Block).where(
            ((Block.blocker_id == viewer_id) & (Block.blocked_id == target_id))
            | ((Block.blocker_id == target_id) & (Block.blocked_id == viewer_id))
        )
    )
    return result.scalar_one_or_none() is not None


async def follow_user(db: AsyncSession, follower_id: str, followee_id: str) -> None:
    existing = await db.execute(
        select(Follow).where(Follow.follower_id == follower_id, Follow.followee_id == followee_id)
    )
    if existing.scalar_one_or_none():
        return  # already following

    db.add(Follow(id=new_uuid(), follower_id=follower_id, followee_id=followee_id))
    # Atomic counter updates — no read-modify-write
    await db.execute(
        text("UPDATE users SET following_count = following_count + 1 WHERE id = :id"),
        {"id": follower_id},
    )
    await db.execute(
        text("UPDATE users SET followers_count = followers_count + 1 WHERE id = :id"),
        {"id": followee_id},
    )


async def unfollow_user(db: AsyncSession, follower_id: str, followee_id: str) -> None:
    result = await db.execute(
        select(Follow).where(Follow.follower_id == follower_id, Follow.followee_id == followee_id)
    )
    follow = result.scalar_one_or_none()
    if not follow:
        return

    await db.delete(follow)
    await db.execute(
        text("UPDATE users SET following_count = GREATEST(following_count - 1, 0) WHERE id = :id"),
        {"id": follower_id},
    )
    await db.execute(
        text("UPDATE users SET followers_count = GREATEST(followers_count - 1, 0) WHERE id = :id"),
        {"id": followee_id},
    )


async def update_profile(db: AsyncSession, user: User, data: ProfileUpdateIn) -> User:
    if data.name is not None:
        user.name = data.name

    profile = user.profile
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)

    for field in ("bio", "ai_since", "location", "website", "twitter", "github_username"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(profile, field, val)

    if data.tool_ids is not None or data.custom_tools is not None:
        await db.execute(delete(UserTool).where(UserTool.user_id == user.id))
        for tool_id in data.tool_ids or []:
            db.add(UserTool(id=new_uuid(), user_id=user.id, tool_id=tool_id))
        for custom in data.custom_tools or []:
            if custom.strip():
                db.add(
                    UserTool(
                        id=new_uuid(),
                        user_id=user.id,
                        tool_id=None,
                        custom_tool_name=custom.strip()[:100],
                    )
                )

    await db.flush()
    return user


async def get_followers(
    db: AsyncSession, user_id: str, limit: int = 20, offset: int = 0
) -> list[User]:
    result = await db.execute(
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.followee_id == user_id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars())


async def get_following(
    db: AsyncSession, user_id: str, limit: int = 20, offset: int = 0
) -> list[User]:
    result = await db.execute(
        select(User)
        .join(Follow, Follow.followee_id == User.id)
        .where(Follow.follower_id == user_id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars())
