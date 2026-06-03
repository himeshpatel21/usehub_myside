"""Redis-backed session store. Sessions are stored as JSON with a rolling TTL."""

import json
import secrets
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

SESSION_PREFIX = "session:"


def _key(session_id: str) -> str:
    return f"{SESSION_PREFIX}{session_id}"


async def create_session(redis: Redis, user_id: str) -> str:
    session_id = secrets.token_urlsafe(32)
    data = {
        "user_id": user_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    await redis.setex(_key(session_id), settings.session_ttl_seconds, json.dumps(data))
    return session_id


async def get_session(redis: Redis, session_id: str) -> dict | None:
    raw = await redis.get(_key(session_id))
    if not raw:
        return None
    data = json.loads(raw)
    # Rolling TTL — refresh on access
    await redis.expire(_key(session_id), settings.session_ttl_seconds)
    return data


async def delete_session(redis: Redis, session_id: str) -> None:
    await redis.delete(_key(session_id))
