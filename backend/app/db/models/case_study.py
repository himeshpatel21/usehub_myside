from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)


class CaseStudy(Base, TimestampMixin):
    __tablename__ = "case_studies"
    __table_args__ = (
        Index("ix_case_studies_author_published", "author_id", "published_at"),
        Index("ix_case_studies_visibility_published", "visibility", "published_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    author_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(350), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # public | unlisted | private
    visibility: Mapped[str] = mapped_column(String(20), default="private", nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applause_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aha_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Unique slug per author
    __table_args__ = (
        UniqueConstraint("author_id", "slug", name="uq_case_study_author_slug"),
        Index("ix_case_studies_author_published", "author_id", "published_at"),
        Index("ix_case_studies_visibility_published", "visibility", "published_at"),
    )

    author: Mapped["User"] = relationship("User")  # noqa: F821
    versions: Mapped[list["CaseStudyVersion"]] = relationship(
        "CaseStudyVersion", back_populates="case_study", cascade="all, delete-orphan"
    )
    tags: Mapped[list["CaseStudyTag"]] = relationship(
        "CaseStudyTag", back_populates="case_study", cascade="all, delete-orphan"
    )


class CaseStudyVersion(Base):
    """Append-only version log. Never update rows — only insert."""

    __tablename__ = "case_study_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_study_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("case_studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # { prompt, iterations: [{input, output, notes}], final_output, notes }
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    change_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case_study: Mapped["CaseStudy"] = relationship("CaseStudy", back_populates="versions")


class CaseStudyTag(Base):
    __tablename__ = "case_study_tags"
    __table_args__ = (UniqueConstraint("case_study_id", "tag_id", name="uq_case_study_tag"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_study_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("case_studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    case_study: Mapped["CaseStudy"] = relationship("CaseStudy", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag")
