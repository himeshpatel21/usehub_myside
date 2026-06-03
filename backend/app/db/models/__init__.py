# Import all models here so Alembic can discover them for autogenerate
from app.db.models.case_study import CaseStudy, CaseStudyTag, CaseStudyVersion, Tag
from app.db.models.engagement import Bookmark, Comment, Reaction
from app.db.models.notification import Notification
from app.db.models.profile import Profile, Project, Tool, UserTool
from app.db.models.social import Block, Follow
from app.db.models.user import OAuthIdentity, User

__all__ = [
    "User",
    "OAuthIdentity",
    "Profile",
    "Tool",
    "UserTool",
    "Project",
    "Follow",
    "Block",
    "CaseStudy",
    "CaseStudyVersion",
    "Tag",
    "CaseStudyTag",
    "Reaction",
    "Comment",
    "Bookmark",
    "Notification",
]
