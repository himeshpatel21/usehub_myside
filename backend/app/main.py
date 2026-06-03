"""UseHub FastAPI application entry point."""

import asyncio
import logging

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.config import get_settings
from app.db.redis import close_redis
from app.middleware.input_size import input_size_middleware
from app.middleware.rate_limit import rate_limit_middleware
from app.modules.auth.router import router as auth_router
from app.modules.case_studies.router import router as case_studies_router
from app.modules.engagement.router import router as engagement_router
from app.modules.feed.router import router as feed_router
from app.modules.media.router import router as media_router
from app.modules.notifications.consumer import run_consumer
from app.modules.notifications.router import router as notifications_router
from app.modules.search.router import router as search_router
from app.modules.users.router import router as users_router

settings = get_settings()

# ── Observability ──────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.2,
        environment=settings.app_env,
    )

# ── App ────────────────────────────────────────────────────────────────────────

_consumer_task: asyncio.Task | None = None


async def lifespan(app: FastAPI):
    global _consumer_task
    _consumer_task = asyncio.create_task(run_consumer())
    yield
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    await close_redis()


app = FastAPI(
    title="UseHub API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

_cors_kwargs: dict = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.app_env == "development":
    # Next.js may use 3001, 3002, etc. when 3000 is taken
    _cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
else:
    _cors_kwargs["allow_origins"] = settings.allowed_origins

app.add_middleware(CORSMiddleware, **_cors_kwargs)

app.middleware("http")(input_size_middleware)
app.middleware("http")(rate_limit_middleware)

# ── Error handlers ─────────────────────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An unexpected error occurred"}},
    )


# ── Routes (all under /api/v1) ─────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(case_studies_router, prefix=API_PREFIX)
app.include_router(engagement_router, prefix=API_PREFIX)
app.include_router(feed_router, prefix=API_PREFIX)
app.include_router(search_router, prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)
app.include_router(media_router, prefix=API_PREFIX)


@app.get("/api/v1/health")
async def health() -> dict:
    from app.db.redis import get_redis_client
    from app.db.session import engine

    status: dict = {"status": "ok", "db": "ok", "redis": "ok"}

    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        status["db"] = "degraded"
        status["status"] = "degraded"

    try:
        redis = get_redis_client()
        await redis.ping()
    except Exception:
        status["redis"] = "degraded"
        status["status"] = "degraded"

    return status
