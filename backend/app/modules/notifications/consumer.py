"""
Background asyncio task that consumes Redis Streams and writes notifications.
Runs inside the FastAPI lifespan so it shares the app process.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid
from app.db.models.case_study import CaseStudy
from app.db.models.notification import Notification
from app.db.models.user import User
from app.db.redis import get_redis_client
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

STREAM_KEY = "stream:events"
CONSUMER_GROUP = "notifications"
CONSUMER_NAME = "worker-1"
BATCH_SIZE = 10
POLL_INTERVAL = 2  # seconds


async def _ensure_group() -> None:
    redis = get_redis_client()
    try:
        await redis.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
    except Exception:
        pass  # Group already exists


async def _handle_event(db: AsyncSession, event: dict) -> None:
    event_type = event.get("type", "")

    if event_type == "reaction.created":
        case_study_id = event.get("case_study_id")
        actor_id = event.get("user_id")
        reaction_type = event.get("reaction_type", "like")

        if not case_study_id or not actor_id:
            return

        cs_result = await db.execute(select(CaseStudy).where(CaseStudy.id == case_study_id))
        cs = cs_result.scalar_one_or_none()
        if not cs or cs.author_id == actor_id:
            return

        actor_result = await db.execute(select(User).where(User.id == actor_id))
        actor = actor_result.scalar_one_or_none()
        if not actor:
            return

        db.add(
            Notification(
                id=new_uuid(),
                recipient_id=cs.author_id,
                type="reaction",
                payload={
                    "actor_handle": actor.handle,
                    "actor_avatar": actor.avatar_url,
                    "actor_name": actor.name,
                    "case_study_id": cs.id,
                    "case_study_title": cs.title,
                    "reaction_type": reaction_type,
                },
            )
        )

    elif event_type == "comment.created":
        case_study_id = event.get("case_study_id")
        actor_id = event.get("user_id")

        if not case_study_id or not actor_id:
            return

        cs_result = await db.execute(select(CaseStudy).where(CaseStudy.id == case_study_id))
        cs = cs_result.scalar_one_or_none()
        if not cs or cs.author_id == actor_id:
            return

        actor_result = await db.execute(select(User).where(User.id == actor_id))
        actor = actor_result.scalar_one_or_none()
        if not actor:
            return

        db.add(
            Notification(
                id=new_uuid(),
                recipient_id=cs.author_id,
                type="comment",
                payload={
                    "actor_handle": actor.handle,
                    "actor_avatar": actor.avatar_url,
                    "actor_name": actor.name,
                    "case_study_id": cs.id,
                    "case_study_title": cs.title,
                },
            )
        )

    elif event_type == "user.followed":
        followee_id = event.get("followee_id")
        follower_id = event.get("follower_id")

        if not followee_id or not follower_id:
            return

        actor_result = await db.execute(select(User).where(User.id == follower_id))
        actor = actor_result.scalar_one_or_none()
        if not actor:
            return

        db.add(
            Notification(
                id=new_uuid(),
                recipient_id=followee_id,
                type="follow",
                payload={
                    "actor_handle": actor.handle,
                    "actor_avatar": actor.avatar_url,
                    "actor_name": actor.name,
                },
            )
        )

    await db.commit()


async def run_consumer() -> None:
    await _ensure_group()
    redis = get_redis_client()
    logger.info("Notification consumer started")

    while True:
        try:
            messages = await redis.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_KEY: ">"},
                count=BATCH_SIZE,
                block=POLL_INTERVAL * 1000,
            )

            if not messages:
                continue

            for _stream, entries in messages:
                for entry_id, data in entries:
                    async with AsyncSessionLocal() as db:
                        try:
                            await _handle_event(db, data)
                            await redis.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
                        except Exception as exc:
                            logger.warning("Failed to handle event %s: %s", entry_id, exc)

        except asyncio.CancelledError:
            logger.info("Notification consumer stopped")
            break
        except Exception as exc:
            logger.error("Consumer error: %s", exc)
            await asyncio.sleep(5)
