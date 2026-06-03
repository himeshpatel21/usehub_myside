from datetime import date

from pydantic import BaseModel, field_validator


class ToolOut(BaseModel):
    id: str
    name: str
    slug: str
    category: str | None = None


class UserToolOut(BaseModel):
    tool: ToolOut | None = None
    custom_tool_name: str | None = None


class ProjectOut(BaseModel):
    id: str
    title: str
    url: str | None = None
    description: str | None = None


class ProfileOut(BaseModel):
    bio: str | None = None
    ai_since: date | None = None
    location: str | None = None
    website: str | None = None
    twitter: str | None = None
    github_username: str | None = None
    tools: list[UserToolOut] = []
    projects: list[ProjectOut] = []


class UserPublicOut(BaseModel):
    id: str
    handle: str
    name: str
    avatar_url: str | None = None
    followers_count: int
    following_count: int
    profile: ProfileOut | None = None
    is_following: bool = False


class ProfileUpdateIn(BaseModel):
    name: str | None = None
    bio: str | None = None
    ai_since: date | None = None
    location: str | None = None
    website: str | None = None
    twitter: str | None = None
    github_username: str | None = None
    tool_ids: list[str] | None = None
    custom_tools: list[str] | None = None

    @field_validator("bio")
    @classmethod
    def bio_max_length(cls, v: str | None) -> str | None:
        if v and len(v) > 1000:
            raise ValueError("Bio must be 1000 characters or fewer")
        return v


class UserMinimalOut(BaseModel):
    id: str
    handle: str
    name: str
    avatar_url: str | None = None
