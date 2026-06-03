from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.profile import Tool
from app.db.models.user import User
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, get_optional_user
from app.modules.case_studies.schemas import CaseStudyListOut
from app.modules.users import service
from app.modules.users.schemas import (
    ProfileOut,
    ProfileUpdateIn,
    ToolOut,
    UserMinimalOut,
    UserPublicOut,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublicOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserPublicOut:
    return _user_to_out(current_user, is_following=False)


@router.patch("/me", response_model=UserPublicOut)
async def update_me(
    data: ProfileUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserPublicOut:
    user = await service.update_profile(db, current_user, data)
    return _user_to_out(user, is_following=False)


@router.get("/me/followers", response_model=list[UserMinimalOut])
async def my_followers(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserMinimalOut]:
    users = await service.get_followers(db, current_user.id, limit, offset)
    return [
        UserMinimalOut(id=u.id, handle=u.handle, name=u.name, avatar_url=u.avatar_url)
        for u in users
    ]


@router.get("/me/following", response_model=list[UserMinimalOut])
async def my_following(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserMinimalOut]:
    users = await service.get_following(db, current_user.id, limit, offset)
    return [
        UserMinimalOut(id=u.id, handle=u.handle, name=u.name, avatar_url=u.avatar_url)
        for u in users
    ]


@router.get("/{handle}", response_model=UserPublicOut)
async def get_user(
    handle: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> UserPublicOut:
    user = await service.get_user_by_handle(db, handle)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return 404 if viewer is blocked (don't leak that account exists)
    if current_user and await service.is_blocked(db, current_user.id, user.id):
        raise HTTPException(status_code=404, detail="User not found")

    following = False
    if current_user and current_user.id != user.id:
        following = await service.is_following(db, current_user.id, user.id)

    return _user_to_out(user, is_following=following)


@router.post("/{handle}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_user(
    handle: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    target = await service.get_user_by_handle(db, handle)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    await service.follow_user(db, current_user.id, target.id)


@router.delete("/{handle}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    handle: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    target = await service.get_user_by_handle(db, handle)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await service.unfollow_user(db, current_user.id, target.id)


@router.get("/{handle}/case-studies", response_model=list[CaseStudyListOut])
async def get_user_case_studies(
    handle: str,
    limit: int = Query(default=20, le=100),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[CaseStudyListOut]:
    from app.modules.case_studies import service as cs_service
    from app.modules.case_studies.router import _cs_to_list_out

    user = await service.get_user_by_handle(db, handle)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user and await service.is_blocked(db, current_user.id, user.id):
        raise HTTPException(status_code=404, detail="User not found")

    viewer_id = current_user.id if current_user else None
    items = await cs_service.list_user_case_studies(db, user.id, viewer_id, limit, cursor)
    return [_cs_to_list_out(cs) for cs in items]


@router.get("/tools/catalog", response_model=list[ToolOut])
async def get_tools(db: AsyncSession = Depends(get_db)) -> list[ToolOut]:
    result = await db.execute(select(Tool).order_by(Tool.name))
    return [
        ToolOut(id=t.id, name=t.name, slug=t.slug, category=t.category) for t in result.scalars()
    ]


def _user_to_out(user: User, is_following: bool) -> UserPublicOut:
    profile_out = None
    if user.profile:
        p = user.profile
        tools = [{"tool": t.tool, "custom_tool_name": t.custom_tool_name} for t in (p.tools or [])]
        profile_out = ProfileOut(
            bio=p.bio,
            ai_since=p.ai_since,
            location=p.location,
            website=p.website,
            twitter=p.twitter,
            github_username=p.github_username,
            tools=tools,
            projects=[
                {"id": pr.id, "title": pr.title, "url": pr.url, "description": pr.description}
                for pr in (p.projects or [])
            ],
        )
    return UserPublicOut(
        id=user.id,
        handle=user.handle,
        name=user.name,
        avatar_url=user.avatar_url,
        followers_count=user.followers_count,
        following_count=user.following_count,
        profile=profile_out,
        is_following=is_following,
    )
