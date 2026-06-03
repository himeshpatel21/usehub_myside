from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_since: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    twitter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="profile")  # noqa: F821
    tools: Mapped[list["UserTool"]] = relationship(
        "UserTool",
        primaryjoin="Profile.user_id == UserTool.user_id",
        foreign_keys="UserTool.user_id",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        primaryjoin="Profile.user_id == Project.user_id",
        foreign_keys="Project.user_id",
        cascade="all, delete-orphan",
    )


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)


class UserTool(Base):
    __tablename__ = "user_tools"
    __table_args__ = (UniqueConstraint("user_id", "tool_id", name="uq_user_tool"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tools.id", ondelete="CASCADE"), nullable=True
    )
    custom_tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    tool: Mapped["Tool | None"] = relationship("Tool")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
