from datetime import datetime

from pydantic import BaseModel, field_validator


class IterationIn(BaseModel):
    input: str
    output: str
    notes: str | None = None

    @field_validator("input", "output")
    @classmethod
    def max_length(cls, v: str) -> str:
        if len(v) > 20_000:
            raise ValueError("Field exceeds 20,000 character limit")
        return v


class CaseStudyContentIn(BaseModel):
    prompt: str
    iterations: list[IterationIn] = []
    final_output: str
    notes: str | None = None

    @field_validator("prompt")
    @classmethod
    def prompt_max(cls, v: str) -> str:
        if len(v) > 10_000:
            raise ValueError("Prompt exceeds 10,000 character limit")
        return v

    @field_validator("iterations")
    @classmethod
    def iterations_max(cls, v: list) -> list:
        if len(v) > 50:
            raise ValueError("Maximum 50 iterations allowed")
        return v

    @field_validator("final_output")
    @classmethod
    def final_output_max(cls, v: str) -> str:
        if len(v) > 50_000:
            raise ValueError("Final output exceeds 50,000 character limit")
        return v


class CaseStudyCreateIn(BaseModel):
    title: str
    summary: str | None = None
    ai_model: str | None = None
    ai_platform: str | None = None
    visibility: str = "private"
    content: CaseStudyContentIn
    tags: list[str] = []
    change_message: str | None = None

    @field_validator("title")
    @classmethod
    def title_max(cls, v: str) -> str:
        if len(v) > 300:
            raise ValueError("Title exceeds 300 character limit")
        return v

    @field_validator("visibility")
    @classmethod
    def valid_visibility(cls, v: str) -> str:
        if v not in ("public", "unlisted", "private"):
            raise ValueError("Visibility must be public, unlisted, or private")
        return v

    @field_validator("tags")
    @classmethod
    def tags_max(cls, v: list) -> list:
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return [t.strip().lower()[:50] for t in v if t.strip()]


class CaseStudyUpdateIn(BaseModel):
    title: str | None = None
    summary: str | None = None
    ai_model: str | None = None
    ai_platform: str | None = None
    visibility: str | None = None
    content: CaseStudyContentIn | None = None
    tags: list[str] | None = None
    change_message: str | None = None


class TagOut(BaseModel):
    id: str
    name: str
    slug: str


class AuthorOut(BaseModel):
    id: str
    handle: str
    name: str
    avatar_url: str | None = None


class CaseStudyOut(BaseModel):
    id: str
    author: AuthorOut
    title: str
    slug: str
    summary: str | None = None
    ai_model: str | None = None
    ai_platform: str | None = None
    visibility: str
    content: dict | None = None
    tags: list[TagOut] = []
    likes_count: int
    applause_count: int
    aha_count: int
    comments_count: int
    current_version_id: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CaseStudyListOut(BaseModel):
    id: str
    author: AuthorOut
    title: str
    slug: str
    summary: str | None = None
    ai_model: str | None = None
    visibility: str
    tags: list[TagOut] = []
    likes_count: int
    applause_count: int
    aha_count: int
    comments_count: int
    published_at: datetime | None = None
    created_at: datetime
