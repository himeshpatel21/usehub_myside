"""OAuth 2.0 authentication routes for Google and GitHub."""

import secrets

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.user import User
from app.db.redis import get_redis_client
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.service import get_or_create_dev_user, upsert_oauth_user
from app.modules.auth.session import create_session, delete_session

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

OAUTH_STATE_TTL = 600  # 10 minutes

PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": "openid email profile",
        "client_id_key": "google_client_id",
        "client_secret_key": "google_client_secret",
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": "read:user user:email",
        "client_id_key": "github_client_id",
        "client_secret_key": "github_client_secret",
    },
}


def _callback_url(provider: str) -> str:
    return f"{settings.frontend_url}/api/auth/callback/{provider}"


class DevLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login/email")
async def dev_login(
    body: DevLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if settings.app_env == "production":
        raise HTTPException(status_code=404, detail="Not found")

    ok_user = secrets.compare_digest(
        body.username.encode(), settings.dev_login_username.encode()
    )
    ok_pass = secrets.compare_digest(
        body.password.encode(), settings.dev_login_password.encode()
    )
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = await get_or_create_dev_user(
        db,
        handle=settings.dev_login_username,
        name="Max",
        email="max@dev.local",
    )
    redis = get_redis_client()
    session_id = await create_session(redis, user.id)

    is_prod = settings.app_env == "production"
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
    )
    return {"handle": user.handle}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "id": current_user.id,
        "handle": current_user.handle,
        "name": current_user.name,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url,
        "followers_count": current_user.followers_count,
        "following_count": current_user.following_count,
    }


@router.post("/logout")
async def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias="usehub_session"),
) -> dict:
    if session_token:
        redis = get_redis_client()
        await delete_session(redis, session_token)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"ok": True}


@router.get("/{provider}")
async def oauth_redirect(provider: str) -> Response:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown provider")

    cfg = PROVIDERS[provider]
    client_id = getattr(settings, cfg["client_id_key"])
    if not client_id:
        raise HTTPException(status_code=503, detail=f"{provider} OAuth not configured")

    state = secrets.token_urlsafe(16)
    redis = get_redis_client()
    await redis.setex(f"oauth_state:{state}", OAUTH_STATE_TTL, provider)

    async with AsyncOAuth2Client(
        client_id=client_id,
        redirect_uri=_callback_url(provider),
    ) as client:
        uri, _ = client.create_authorization_url(
            cfg["authorize_url"], state=state, scope=cfg["scopes"]
        )

    return Response(status_code=302, headers={"Location": uri})


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown provider")

    redis = get_redis_client()
    stored_provider = await redis.get(f"oauth_state:{state}")
    if not stored_provider or stored_provider != provider:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    await redis.delete(f"oauth_state:{state}")

    cfg = PROVIDERS[provider]
    client_id = getattr(settings, cfg["client_id_key"])
    client_secret = getattr(settings, cfg["client_secret_key"])

    async with AsyncOAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=_callback_url(provider),
    ) as client:
        token = await client.fetch_token(cfg["token_url"], code=code)
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        if provider == "github":
            headers["Accept"] = "application/json"
        resp = await client.get(cfg["userinfo_url"], headers=headers)
        resp.raise_for_status()
        userinfo = resp.json()

    email, name, avatar_url, provider_user_id = _extract_userinfo(provider, userinfo)

    # GitHub may require a separate email fetch
    if provider == "github" and not email:
        async with AsyncOAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
        ) as client:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {token['access_token']}"},
            )
            for e in emails_resp.json():
                if e.get("primary") and e.get("verified"):
                    email = e["email"]
                    break

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from provider")

    user = await upsert_oauth_user(db, provider, provider_user_id, email, name, avatar_url)
    session_id = await create_session(redis, user.id)

    is_prod = settings.app_env == "production"
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
    )
    return {"handle": user.handle}


def _extract_userinfo(provider: str, info: dict) -> tuple[str, str, str | None, str]:
    if provider == "google":
        return (
            info.get("email", ""),
            info.get("name", info.get("email", "")),
            info.get("picture"),
            info["sub"],
        )
    elif provider == "github":
        return (
            info.get("email", ""),
            info.get("name") or info.get("login", ""),
            info.get("avatar_url"),
            str(info["id"]),
        )
    raise ValueError(f"Unknown provider: {provider}")
