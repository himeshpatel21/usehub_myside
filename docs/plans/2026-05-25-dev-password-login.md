# Dev Password Login (skip OAuth)

**Date:** 2026-05-25

## Goal

Allow local development access without configuring Google or GitHub OAuth. Sign in with username `max` / password `mustermann` via a dev-only endpoint.

## Approach

Add `POST /api/v1/auth/login/email` that compares credentials to env-configured values, creates the dev user in the DB on first use, and issues the same Redis session cookie the OAuth flow uses. The endpoint returns 404 in production. Frontend shows a dev-only form below OAuth buttons.

## Steps

- [x] `backend/app/config.py` — add `dev_login_username: str = "max"` and `dev_login_password: str = "mustermann"`
- [x] `.env.example` — document `DEV_LOGIN_USERNAME` / `DEV_LOGIN_PASSWORD`
- [x] `backend/app/modules/auth/service.py` — add `get_or_create_dev_user(db, handle, name, email)`
- [x] `backend/app/modules/auth/router.py` — add `DevLoginRequest` model and `POST /login/email` route before `GET /{provider}`
- [x] `backend/tests/test_dev_login.py` — mocked tests for success (max/mustermann) and invalid credentials
- [x] `frontend/lib/api.ts` — add `auth.devLogin(username, password)`
- [x] `frontend/app/login/page.tsx` — dev form shown when `NODE_ENV === "development"`
- [x] `README.md` — add "Dev login" section under OAuth setup

## Key decisions

- Credentials stored in env settings, not the database — no `password` column needed, no DB migration
- `secrets.compare_digest` on encoded strings to avoid timing attacks
- Routes must be registered **before** `GET /{provider}`: `/login/email`, `/me`, and `/logout` (otherwise `/me` is treated as an OAuth provider and returns "Unknown provider")
- [x] Fix: move `GET /auth/me` above `GET /auth/{provider}` (2026-05-25)
- Tests mock `get_or_create_dev_user` and `create_session` so they run without Postgres/Redis
- Endpoint is 404 in production; safe to leave deployed
