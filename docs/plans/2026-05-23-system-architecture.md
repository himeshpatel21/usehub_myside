# UseHub — High-Level System Architecture

**Date:** 2026-05-23
**Status:** Draft v1 (architecture only, no code)
**Author:** System design pass

---

## 0. Goal

Design a **GitHub-like platform for AI case studies** with a Facebook-style social layer that:

- Boots as an **MVP-grade modular monolith** (fast to ship, easy to operate).
- Has **clear bounded contexts** so services can be peeled off as load grows.
- Scales cleanly from **1K → 1M users** without a ground-up rewrite.
- Leaves seams for **versioning, marketplace, and ads** without leaking those concerns into v1.

Non-goals for v1: real-time collaboration, on-platform AI inference, ad serving, payments.

---

## 1. High-Level System Architecture

```
                ┌─────────────────────────────────────────┐
                │                Clients                  │
                │   Web (Next.js)   •   Mobile (later)    │
                └───────────────┬─────────────────────────┘
                                │ HTTPS
                        ┌───────▼────────┐
                        │      CDN       │  static assets + cached public pages
                        │ (Cloudflare)   │
                        └───────┬────────┘
                                │
                        ┌───────▼────────┐
                        │  API Gateway / │  TLS, WAF, auth check, rate limit
                        │  Load Balancer │
                        └───────┬────────┘
                                │
            ┌───────────────────▼────────────────────┐
            │       Application Tier (Monolith)      │
            │  ┌────────┬─────────┬──────┬────────┐  │
            │  │ User   │ Case    │ Feed │ Engage │  │  ← bounded modules
            │  │ svc    │ Study   │ svc  │ ment   │  │
            │  └────────┴─────────┴──────┴────────┘  │
            │  Auth · Notifications · Search · Jobs  │
            └───┬─────────────┬──────────────┬───────┘
                │             │              │
        ┌───────▼───┐   ┌─────▼─────┐  ┌─────▼──────┐
        │ PostgreSQL│   │   Redis   │  │ Object     │
        │ (primary  │   │  cache /  │  │ Storage    │
        │  +replica)│   │  queues   │  │ (S3 +CDN)  │
        └───────────┘   └───────────┘  └────────────┘

        Async workers ──► email, feed fanout, image processing
        OAuth providers ──► Google, GitHub, (later) Microsoft, Apple
```

### Stack choices and why

| Layer | Choice (v1) | Why |
|---|---|---|
| Frontend | **Next.js (React) + Tailwind** | SSR/ISR for SEO on public case studies, great DX, edge-cacheable |
| Backend | **Modular monolith** (e.g. Node/NestJS or Python/FastAPI or Go) | Single deploy, fast iteration, clean modules → easy to extract later |
| API style | **REST + JSON** for v1, GraphQL/BFF only if/when the client demands it | Boring, debuggable, fits CDN caching |
| Database | **PostgreSQL 16** (managed: RDS / Cloud SQL / Neon) | ACID, JSONB for flexible case-study content, FTS built-in, pgvector for future semantic search |
| Cache / queues | **Redis** | Sessions, feed sorted-sets, counters, rate limiting, lightweight job queue |
| Object storage | **S3-compatible** (AWS S3 / R2) | Avatars, attachments, exported case-study artifacts; never store blobs in PG |
| CDN | **Cloudflare / CloudFront** | Public profile + public case study pages should be edge-cached |
| Auth | **OAuth 2.1 / OIDC** (Google + GitHub first) + email magic link fallback | No password storage, leverages provider security |
| Sessions | **HTTP-only secure cookie → opaque session id → Redis** | Easy revocation, no JWT footguns at MVP |
| Background jobs | **BullMQ / Celery / asynq** on Redis | Notifications, feed fanout, image transcode |
| Search | **Postgres FTS + trigram** v1 → **OpenSearch** at ~100K users | Avoid premature complexity |
| Observability | **OpenTelemetry** → Grafana Cloud / Datadog; **Sentry** for errors | Day-1 cheap, scales with you |
| CI/CD | GitHub Actions → container image → managed PaaS (Fly/Render/Railway) → later K8s | Ship daily |

### Architectural principles

1. **Modular monolith, microservice-shaped internals.** Each "service" below is a module with its own folder, its own Postgres schema, and a **typed internal API**. Cross-module calls go through that API only — never direct DB joins across modules. The day you extract `feed` into its own deployable, you swap the in-process call for HTTP/gRPC and nothing else changes.
2. **Domain events from day one.** Mutations publish events (`case_study.published`, `reaction.created`, `user.followed`) onto an internal bus (Redis Streams v1, Kafka later). Notifications, feed fanout, and analytics subscribe. This is the single biggest unlock for future scaling.
3. **PostgreSQL is the source of truth.** Everything else (Redis, search, feed) is a derived, rebuildable cache.
4. **Public-by-default content is cache-friendly.** Public case studies and profiles render as static-ish pages with short TTLs at the CDN — this alone absorbs 80% of read traffic.
5. **Design for versioning, even if you don't ship it.** Case-study content lives in an append-only `case_study_versions` table from v1. We just always read "current". GitHub-style diffs become a UI feature, not a migration.

---

## 2. Main System Components

Each is a **module** inside the monolith today, designed to be a **service** tomorrow.

### 2.1 User Service (Identity & Profile)

**Responsibilities**
- OAuth login flow (Google, GitHub) + account linking.
- Session lifecycle (issue, refresh, revoke).
- Profile: handle, display name, avatar, bio, `ai_since` date, tools used, projects built.
- Social graph: follow / unfollow / block.

**Owns tables:** `users`, `oauth_identities`, `sessions`, `profiles`, `tools`, `user_tools`, `projects`, `follows`, `blocks`.

**Publishes events:** `user.created`, `user.followed`, `user.blocked`.

**Why isolate it:** Identity is the only module that touches OAuth tokens and PII — keeping it bounded simplifies compliance (GDPR delete-me, audit logs) and is the natural first extraction target.

---

### 2.2 Case Study Service (Posts)

**Responsibilities**
- CRUD on case studies and their **versions** (immutable revisions).
- Structured content: `prompt`, `iterations[]`, `ai_model`, `ai_platform`, `final_output`, attachments.
- Visibility: `public` / `unlisted` / `private`.
- Tagging, slugs, drafts.

**Owns tables:** `case_studies`, `case_study_versions`, `attachments`, `tags`, `case_study_tags`.

**Publishes events:** `case_study.published`, `case_study.updated`, `case_study.deleted`.

**Key design choice — versioning from day 1**
- `case_studies` holds metadata + pointer to `current_version_id`.
- `case_study_versions` is **append-only** (`version_number`, JSONB `content`, `change_message`, `created_at`).
- v1 always points current = latest; v2 ships diffs and a "history" tab without any schema change.

---

### 2.3 Feed Service

**Responsibilities**
- Build the home feed for a logged-in user.
- Build the discovery / trending feed for everyone.
- Maintain per-user feed caches.

**Strategy: hybrid fan-out** (the Twitter playbook, sized for our scale)
- **Fan-out on write** for normal users: when an author with ≤ 10K followers publishes, enqueue a job that pushes the case_study_id into each follower's Redis sorted-set (`feed:{user_id}` scored by timestamp/rank). Reads are O(log N).
- **Fan-out on read** for power users: authors above the threshold are stored separately; at read time we merge "stored feed" + "recent posts from heavy authors I follow". Avoids the celebrity write-amplification problem.
- **Trending / discovery feed:** materialized periodically by a worker from engagement events; cached globally.

**Owns:** Redis keyspace (`feed:*`, `trending:*`). Source of truth remains Postgres.

---

### 2.4 Engagement Service

**Responsibilities**
- Reactions: `like`, `applause`, `aha` (and easy to add more — it's an enum + counter).
- Comments (flat in v1, threaded in v2).
- Bookmarks.
- Counter maintenance (likes_count, comments_count, etc.).

**Owns tables:** `reactions`, `comments`, `bookmarks`, `engagement_counters`.

**Counter strategy**
- v1: update denormalized counters in same transaction as the action — simple, fine up to ~100K users.
- Scale step: move counters to **Redis HINCRBY** + periodic flush to Postgres; reactions table remains the auditable source of truth.

**Publishes events:** `reaction.created`, `comment.created` — Feed and Notifications subscribe.

---

### 2.5 Supporting modules (also designed in, lightly shipped)

| Module | v1 | Scales into |
|---|---|---|
| **Auth** | OAuth + cookie sessions in Redis | OIDC provider abstraction, SSO for enterprise |
| **Notifications** | In-app only, populated by event consumers | Email + push + digest emails |
| **Search** | Postgres FTS over case_studies + users | OpenSearch cluster, vector search via pgvector or Pinecone |
| **Media** | Direct-to-S3 presigned uploads + on-the-fly resize via CDN worker | Dedicated image service, video transcode pipeline |
| **Moderation** | Report endpoint + manual review queue | Automated NSFW/abuse classifiers, trust & safety dashboard |
| **Marketplace** (future) | `listings`, `orders`, `payouts`; Stripe Connect | Escrow, disputes, commission ledger |
| **Ads** (future) | `campaigns`, `creatives`, `impressions` | Auction service, targeting, billing |
| **Analytics** | Postgres + simple dashboards | CDC → warehouse (BigQuery/Snowflake) |

---

## 3. Data Model (entities & relationships)

Showing **what** and **how it relates**, not SQL.

### Core entities

- **User** — id, handle, email, name, avatar_url, bio, ai_since (date), created_at.
- **OAuthIdentity** — user_id, provider, provider_user_id, linked_at. (One user can link multiple providers.)
- **Session** — id, user_id, created_at, last_seen_at, ip, user_agent, revoked_at. (Stored in Redis with a thin audit copy in PG.)
- **Profile** — extends User: long-form bio, location, website, social links. (Split from `users` so identity stays small and hot.)
- **Tool** — id, name, slug, category. Canonical catalog ("ChatGPT", "Claude", "Midjourney", "Cursor"…).
- **UserTool** — user_id × tool_id (the "tools used" list on the profile).
- **Project** — id, user_id, title, url, description, created_at. (The "projects built" list.)
- **Follow** — follower_id, followee_id, created_at.
- **Block** — blocker_id, blocked_id, created_at.

### Content entities

- **CaseStudy** — id, author_id, title, slug, summary, ai_model, ai_platform, visibility (`public`/`unlisted`/`private`), current_version_id, likes_count, comments_count, created_at, updated_at, published_at.
- **CaseStudyVersion** — id, case_study_id, version_number, content (JSONB: `{ prompt, iterations[], final_output, notes }`), change_message, created_at. **Append-only.**
- **Attachment** — id, version_id, storage_key, mime_type, size_bytes, width, height.
- **Tag** — id, name, slug.
- **CaseStudyTag** — case_study_id × tag_id.

### Engagement entities

- **Reaction** — id, user_id, target_type (`case_study`|`comment`), target_id, reaction_type (`like`|`applause`|`aha`), created_at. Unique on (user_id, target_type, target_id, reaction_type).
- **Comment** — id, case_study_id, user_id, parent_id (nullable, for future threading), body, created_at, deleted_at.
- **Bookmark** — user_id × case_study_id, created_at.

### Derived / ephemeral

- **FeedItem** — *Redis only.* Per-user sorted set `feed:{user_id}` of case_study_ids scored by rank.
- **Notification** — id, recipient_id, type, payload (JSONB), read_at, created_at.
- **EngagementCounter** — target_type, target_id, likes_count, applause_count, aha_count, comments_count (Redis-first, periodically flushed to PG).

### Future entities (shape only)

- **Listing** — case_study_id, creator_id, price, currency, status.
- **Order** — listing_id, buyer_id, amount, commission, status, stripe_payment_intent_id.
- **AdCampaign / AdCreative / AdImpression** — for the ads roadmap.

### Relationship summary

```
User 1───N CaseStudy 1───N CaseStudyVersion
User N───N User  (Follow, Block)
User N───N Tool  (UserTool)
User 1───N Project
User N───N CaseStudy  (Reaction, Bookmark)
CaseStudy N───N Tag
CaseStudy 1───N Comment ───┐
                           └─ self-ref (parent_id) for threads
CaseStudyVersion 1───N Attachment
```

### Indexing & query patterns to plan for

- `case_studies (author_id, published_at DESC)` — profile page.
- `case_studies (visibility, published_at DESC)` — discovery.
- `follows (follower_id)` and `(followee_id)` — feed building, profile counts.
- `reactions (target_type, target_id)` — counts and "who reacted".
- GIN index on `case_study_versions.content` and on `tags` for FTS.
- Partition `reactions` and `notifications` by month once tables get big (post-100K users).

---

## 4. Scaling Path: 1K → 10K → 100K → 1M

The plan is to **change one thing at a time**, driven by metrics, not vibes.

### Stage 1 — 1K users (MVP, "does it work?")

- Single PaaS app instance (Fly/Render/Railway).
- 1 managed Postgres (small), 1 managed Redis.
- 1 S3 bucket + Cloudflare in front.
- All modules in one process, jobs in same process or one worker.
- Auth: Google + GitHub OAuth, sessions in Redis.
- Observability: structured logs + Sentry + a basic uptime check.
- **Cost:** < $100/mo.
- **Bottleneck you'll hit:** none — focus on product, not infra.

### Stage 2 — 10K users ("it's working, don't break it")

- **Horizontal scale** the app behind a load balancer (2–4 instances). Stateless web tier, sessions already in Redis.
- **Postgres read replica.** Route profile reads, public case-study reads, and feed reads to the replica.
- **Split the worker** out of the web process (separate deployable, same image).
- **CDN aggressively** in front of public pages (ISR for case studies, edge cache for profiles).
- **Search:** still Postgres FTS + trigram, now with proper indexes.
- **Connection pooling** with PgBouncer if connection counts climb.
- **Cost:** ~$500–$1.5K/mo.
- **Bottleneck you'll hit:** feed query getting expensive on hot users → introduces Stage 3.

### Stage 3 — 100K users ("the architecture starts paying off")

- **Activate the hybrid feed fan-out** (Redis sorted sets, fan-out-on-write job for normal users, fan-out-on-read merge for heavy followers).
- **Redis cluster** (or managed Redis with replicas) — sessions, feed, counters, rate limits.
- **Engagement counters move to Redis** with a periodic flush job; reactions table partitioned by month.
- **Promote a service:** extract `feed` (and probably `notifications`) into their own deployables. They consume events; they don't need a new DB yet (separate schema, same cluster, dedicated replica).
- **Search:** stand up **OpenSearch / Elasticsearch**, index case studies and users via CDC or event consumer.
- **Media pipeline:** dedicated image-resize worker, signed URLs for private content, video transcode if videos are added.
- **Event bus:** if Redis Streams is creaking, move to **Kafka / Redpanda**.
- **CDC** (Debezium) → cheap analytics warehouse (BigQuery / ClickHouse).
- **Multi-AZ** for Postgres and Redis. Backups + PITR validated by drills.
- **Cost:** ~$5K–$15K/mo.
- **Bottleneck you'll hit:** single Postgres write throughput; some tables hot.

### Stage 4 — 1M users ("real platform")

- **Extract services** along the bounded contexts already defined: `user`, `case-study`, `feed`, `engagement`, `notifications`, `marketplace`. Each owns its DB schema; cross-service reads go through APIs or via the event log.
- **Shard Postgres** by `user_id` (Citus, Vitess-on-MySQL is not an option here, or app-level sharding). Most data is naturally user-keyed — case studies, reactions, bookmarks all follow the author or actor.
- **API gateway** (Kong / Envoy / managed): auth, rate limiting, routing, request signing.
- **Caching tiers:** CDN edge → service-level Redis → DB. Public case-study pages should rarely touch the origin.
- **Real-time** via a WebSocket gateway (Soketi / managed Pusher / custom) for notifications and live engagement counts.
- **Multi-region read replicas**; eventually active/active for static content. Writes stay primary-region for v1 of multi-region.
- **Dedicated search and recommendations cluster.** Begin ranking the feed with ML (not just recency) — pgvector or a vector DB for "similar case studies" and personalization.
- **Marketplace goes live:** Stripe Connect, escrow ledger, payouts, commission accounting in a double-entry table. This must be in its own service because money + audit.
- **Ads go live:** auction service, targeting via the analytics warehouse, billing pipeline.
- **Strong observability:** distributed tracing across services, SLOs per endpoint, on-call rotation, runbooks.
- **Cost:** ~$50K+/mo, but unit economics now matter more than absolute cost.

### Cross-cutting scaling levers (apply at every stage)

- **Public content is cache-friendly** — always exploit that first before adding capacity.
- **Counters become Redis + flush** before they become a sharding problem.
- **Hot tables get partitioned** (reactions, notifications, feed-related) before they get sharded.
- **Heavy paths are async** — anything not on the critical user response goes to a job queue.
- **Backpressure** via rate limits and circuit breakers between services.
- **Cost ≈ reads.** Optimize read paths (CDN, materialized feeds, denormalized counters) more aggressively than write paths.

---

## 5. Cross-Cutting Concerns

### Security

- **No passwords stored** — OAuth only (+ magic-link fallback). Provider tokens encrypted at rest if we keep them.
- **Session cookies:** `HttpOnly`, `Secure`, `SameSite=Lax`, short rolling TTL, server-side revocable.
- **Authorization** as a single middleware layer: every read goes through a visibility check (`public` / `unlisted` / `private` + author / blocked / follower). Centralize so cache keys can include visibility.
- **Private case studies** served via **signed S3 URLs** with short TTL; CDN must respect cache-key on auth.
- **CSRF** via double-submit cookie on state-changing endpoints; **CORS** locked down.
- **Secrets** in a secret manager (AWS SM / Doppler), never in env files in the repo.
- **Audit log** for sensitive actions (login, profile change, visibility change, marketplace events).

### Privacy & compliance

- GDPR-style **export** and **delete-me** endpoints — feasible because user-owned data is centralized in the User module.
- PII minimization: profiles store only what's needed; analytics events are pseudonymous.
- Retention policy on sessions, notifications, raw events.

### Reliability

- SLOs from day 1, even if loose: 99.5% for v1, tighten later.
- **Backups** with PITR on Postgres; **restore drills** quarterly.
- **Idempotency keys** on writes that may retry (reactions, version commits, payments).
- **Feature flags** for risky changes (e.g. switching feed strategy).

### Developer experience (so the team stays fast)

- Single repo, modules clearly bounded.
- A typed internal API between modules — extracting a service later is a mechanical change.
- One-command local dev (Docker Compose: app + PG + Redis + MinIO).
- Migrations versioned; one migration per PR.

---

## 6. Open Questions / Decisions to Confirm Before Building

1. **Backend language** — Node/TypeScript (NestJS) vs Python (FastAPI) vs Go. All three are fine; pick by team strength. Recommendation: **Node + TypeScript** because the same language across web + API + workers reduces friction for a small team.
2. **Hosting target** — managed PaaS (Fly/Render) vs AWS from day 1. Recommendation: **PaaS to 10K, then migrate to AWS/GCP** when you need finer-grained control.
3. **Real-time scope for v1** — none, or just notifications? Recommendation: **none in v1, polling is fine**. Add WebSockets at Stage 3.
4. **Search depth for v1** — title + tags only, or full content? Recommendation: **title + tags + summary**, full content at Stage 3 via OpenSearch.
5. **Versioning UX for v1** — silent (every save is a version, only "latest" shown) or explicit ("commit" button with a message)? Recommendation: **silent v1, explicit v2** — the data model supports either, so this is purely a UX call.

---

## 7. Suggested Build Order (for context only, not part of v1 code)

1. Skeleton: monorepo, CI, Docker Compose, base auth (Google + GitHub OAuth).
2. User module: profiles, follows.
3. Case Study module: CRUD + versions table from the start, public/private, tags.
4. Engagement module: reactions + flat comments + bookmarks.
5. Feed module: simple "people I follow, newest first" against PG; introduce Redis fan-out only when measurements demand it.
6. Discovery: trending list, search, profile pages.
7. Polish: notifications, moderation reports, account deletion.
8. Then — and only then — start the marketplace track.

---

## Completion checklist

- [ ] Stack choices confirmed with the team (language, hosting).
- [ ] Bounded contexts and module boundaries reviewed.
- [ ] Data model reviewed; index plan agreed.
- [ ] Event list (`*.created`, `*.updated`, …) finalized for v1.
- [ ] Observability baseline (logs/metrics/traces/errors) wired before first feature.
- [ ] Migration strategy for versioning agreed (silent vs explicit).
