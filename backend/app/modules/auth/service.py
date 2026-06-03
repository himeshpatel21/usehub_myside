"""Upsert users from OAuth provider data."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid
from app.db.models.profile import Profile
from app.db.models.user import OAuthIdentity, User


async def upsert_oauth_user(
    db: AsyncSession,
    provider: str,
    provider_user_id: str,
    email: str,
    name: str,
    avatar_url: str | None,
) -> User:
    # Check if identity exists
    result = await db.execute(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == provider,
            OAuthIdentity.provider_user_id == provider_user_id,
        )
    )
    identity = result.scalar_one_or_none()

    if identity:
        result = await db.execute(select(User).where(User.id == identity.user_id))
        user = result.scalar_one()
        # Update avatar if provided
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
        return user

    # Check if user with this email exists (account linking)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        handle = await _generate_handle(db, name)
        user = User(
            id=new_uuid(),
            email=email,
            handle=handle,
            name=name,
            avatar_url=avatar_url,
        )
        db.add(user)
        await db.flush()

        # Create empty profile
        profile = Profile(user_id=user.id)
        db.add(profile)

    # Link the OAuth identity
    identity = OAuthIdentity(
        id=new_uuid(),
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
        linked_at=datetime.now(UTC),
    )
    db.add(identity)
    await db.flush()
    return user


async def get_or_create_dev_user(
    db: AsyncSession,
    handle: str,
    name: str,
    email: str,
) -> User:
    result = await db.execute(select(User).where(User.handle == handle))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(id=new_uuid(), email=email, handle=handle, name=name)
    db.add(user)
    await db.flush()
    profile = Profile(user_id=user.id)
    db.add(profile)
    await db.flush()
    return user


async def _generate_handle(db: AsyncSession, name: str) -> str:
    """Generate a unique handle from the user's name."""
    from slugify import slugify

    base = slugify(name, separator="_", max_length=30) or "user"
    handle = base
    counter = 1
    while True:
        result = await db.execute(select(User).where(User.handle == handle))
        if not result.scalar_one_or_none():
            return handle
        handle = f"{base}_{counter}"
        counter += 1
