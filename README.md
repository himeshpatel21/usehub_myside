# UseHub

> The GitHub for AI case studies — share prompts, iterations, and outcomes.

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.x (async) + Alembic
- **Frontend:** Next.js 14 (App Router) + Tailwind CSS + shadcn/ui
- **Database:** PostgreSQL 16
- **Cache / Events:** Redis 7
- **Storage:** S3-compatible (MinIO locally, Cloudflare R2 in production)
- **Deploy:** Fly.io (backend) + Vercel (frontend)

## Local Development

### Prerequisites

- Docker + Docker Compose
- Python 3.12
- Node.js 20

### Start everything

```bash
# Copy env vars
cp .env.example backend/.env

# Start Postgres, Redis, MinIO
docker compose up -d db redis minio

# Backend
cd backend
pip install -e ".[dev]"
alembic upgrade head
python app/db/seed.py         # seed tool catalog
uvicorn app.main:app --reload  # http://localhost:8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev                    # http://localhost:3000
```

### API docs

`http://localhost:8000/api/docs`

### OAuth setup (for auth to work locally)

1. **Google:** [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials) — create OAuth 2.0 client, add `http://localhost:3000/api/auth/callback/google` as redirect URI
2. **GitHub:** [github.com/settings/developers](https://github.com/settings/developers) — create OAuth App, callback `http://localhost:3000/api/auth/callback/github`

Add credentials to `backend/.env`.

### Dev login (no OAuth required)

While setting up OAuth, you can sign in with a local dev account:

- Open `http://localhost:3000/login` and use the **Development login** form (shown only in development mode)
- Username: `max` — Password: `mustermann`

Or directly via curl:

```bash
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login/email \
  -H 'Content-Type: application/json' \
  -d '{"username":"max","password":"mustermann"}'
```

This endpoint returns **404** in production (`APP_ENV=production`). Credentials can be overridden via `DEV_LOGIN_USERNAME` / `DEV_LOGIN_PASSWORD` in `backend/.env`.

## Project Structure

```
usehub/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── db/
│   │   │   ├── models/          # SQLAlchemy models (all tables)
│   │   │   ├── session.py       # Async session factory
│   │   │   └── redis.py         # Redis client
│   │   ├── middleware/          # Rate limiting, input size
│   │   └── modules/             # Feature modules (bounded contexts)
│   │       ├── auth/            # OAuth + session management
│   │       ├── users/           # Profiles + social graph
│   │       ├── case_studies/    # Posts + versioning
│   │       ├── engagement/      # Reactions, comments, bookmarks
│   │       ├── feed/            # Home feed + discovery
│   │       ├── search/          # Postgres FTS
│   │       ├── notifications/   # Event consumer + API
│   │       └── media/           # Presigned uploads
│   └── alembic/                 # Database migrations
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # React components
│   └── lib/                     # API client + utilities
├── docs/plans/                  # Architecture documents
├── docker-compose.yml
└── fly.toml                     # Production deployment config
```

## Deployment

### Backend (Fly.io)

```bash
fly launch          # first time
fly secrets set DATABASE_URL=... REDIS_URL=... GOOGLE_CLIENT_ID=... # etc.
fly deploy
```

### Frontend (Vercel)

```bash
vercel --cwd frontend
# Set NEXT_PUBLIC_API_URL to your Fly.io backend URL
```

## Architecture

See [docs/plans/2026-05-23-system-architecture.md](docs/plans/2026-05-23-system-architecture.md) for the full system architecture, scaling strategy, and data model.

## Running Tests

```bash
cd backend
pytest -v
```
