from datetime import datetime

from pydantic import BaseModel, field_validator


class ReactionIn(BaseModel):
    reaction_type: str

    @field_validator("reaction_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        if v not in ("like", "applause", "aha"):
            raise ValueError("reaction_type must be like, applause, or aha")
        return v


class ReactionCountsOut(BaseModel):
    likes_count: int
    applause_count: int
    aha_count: int
    user_reactions: list[str] = []


class CommentIn(BaseModel):
    body: str
    parent_id: str | None = None

    @field_validator("body")
    @classmethod
    def body_max(cls, v: str) -> str:
        if len(v.strip()) == 0:
            raise ValueError("Comment body cannot be empty")
        if len(v) > 2000:
            raise ValueError("Comment exceeds 2,000 character limit")
        return v


class CommentAuthorOut(BaseModel):
    id: str
    handle: str
    name: str
    avatar_url: str | None = None


class CommentOut(BaseModel):
    id: str
    author: CommentAuthorOut
    body: str
    parent_id: str | None = None
    created_at: datetime
    deleted_at: datetime | None = None
