from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "UseHub"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "changeme-in-production-use-a-long-random-string"
    frontend_url: str = "http://localhost:3000"
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://usehub:usehub@localhost:5432/usehub"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Sessions
    session_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days
    session_cookie_name: str = "usehub_session"

    # OAuth — Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # OAuth — GitHub
    github_client_id: str = ""
    github_client_secret: str = ""

    # Object storage (S3 / R2)
    storage_endpoint_url: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "usehub"
    storage_public_url: str = "http://localhost:9000/usehub"

    # Dev login (non-production only)
    dev_login_username: str = "max"
    dev_login_password: str = "mustermann"

    # Sentry
    sentry_dsn: str = ""

    # Rate limits
    rate_limit_post_per_hour: int = 100
    rate_limit_get_per_hour: int = 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()
