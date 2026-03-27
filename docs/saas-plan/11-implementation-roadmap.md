# 11 — Implementation Roadmap

## Phase Overview

| Phase | Name | Duration | Milestone |
|-------|------|----------|-----------|
| **0** | Foundation | Week 1-2 | Pipeline adapter + Docker + DB schema |
| **1** | Core SaaS | Week 3-5 | Auth + jobs API + Celery workers + basic UI |
| **2** | Billing & Storage | Week 6-7 | Stripe + S3 + usage limits |
| **3** | Teams & Channels | Week 8-10 | YouTube OAuth + teams + agency features |
| **4** | Polish & Launch | Week 11-12 | Frontend polish, monitoring, landing page |
| **5** | Growth | Week 13+ | Advanced features, optimization, scale |

---

## Phase 0: Foundation (Week 1-2)

**Goal:** Get the pipeline callable from Python code (not just CLI), set up the
development infrastructure.

### Tasks

#### P0-1: Pipeline Adapter Layer
- [ ] Create `pipeline/adapter.py` with `PipelineJob` class (see 05-pipeline-adapter.md)
- [ ] Add `JobConfig` dataclass to `pipeline/config.py`
- [ ] Modify `pipeline/draft.py` — add `config: JobConfig = None` parameter
- [ ] Modify `pipeline/broll.py` — add config injection + parallel generation
- [ ] Modify `pipeline/voiceover.py` — add config injection
- [ ] Modify `pipeline/captions.py` — cache Whisper model at module level
- [ ] Modify `pipeline/upload.py` — add OAuth credential injection
- [ ] Modify `pipeline/state.py` — add `start_stage()` and progress callback
- [ ] Modify `pipeline/music.py` — add config injection
- [ ] Write tests for `PipelineJob` (mock all API calls)
- [ ] Verify existing CLI still works (backward compatibility)
- [ ] Replace `openai-whisper` with `faster-whisper` (CTranslate2, 4x faster, 4x less memory)

**Key principle:** All changes are additive. New `config` parameter defaults to `None`,
preserving existing behavior.

#### P0-2: Monorepo + Project Structure (see [02a-monorepo.md](../saas-plan/02a-monorepo.md))
- [ ] Initialize pnpm + Turborepo at repo root
- [ ] Create `pnpm-workspace.yaml`, root `package.json`, `turbo.json`
- [ ] Create `apps/web/` — scaffold Next.js 15 project with TypeScript, Tailwind, shadcn/ui
- [ ] Create `apps/api/` — FastAPI app with `package.json` shim for Turborepo
- [ ] Create `packages/ui/` — shared UI component library (shadcn components)
- [ ] Create `packages/tsconfig/` — shared TypeScript configs
- [ ] Create `packages/eslint-config/` — shared ESLint configs
- [ ] Create `requirements-saas.txt` with FastAPI, Celery, SQLAlchemy, etc.
- [ ] Create `.env.example` with all environment variables
- [ ] Create `docker/Dockerfile.api` and `docker/Dockerfile.worker`
- [ ] Create `docker/docker-compose.yml` for local dev
- [ ] Verify `pnpm dev` starts web + api in parallel
- [ ] Verify `docker-compose up` starts all services

#### P0-3: Database Setup
- [ ] Create `saas/settings.py` with Pydantic Settings
- [ ] Create all SQLAlchemy models (see 03-database-schema.md):
  - `saas/models/user.py` — User, OAuthConnection, UserAPIKey
  - `saas/models/team.py` — Team, TeamMember, TeamInvite
  - `saas/models/job.py` — Job, JobStage
  - `saas/models/video.py` — Video
  - `saas/models/channel.py` — YouTubeChannel
  - `saas/models/subscription.py` — Plan, Subscription, UsageRecord
  - `saas/models/api_keys.py` — UserProviderKey
- [ ] Set up Alembic, create initial migration
- [ ] Run migration, verify schema in PostgreSQL
- [ ] Seed plans table (Free, Creator, Pro, Agency, Enterprise)

**Deliverable:** Pipeline callable from Python. Docker dev stack running. DB schema
created. Ready for API development.

---

## Phase 1: Core SaaS (Week 3-5)

**Goal:** Users can register, submit jobs, and watch them complete via the API.

### Tasks

#### P1-1: Authentication
- [ ] Create `saas/services/auth_service.py` — JWT creation, password hashing
- [ ] Create `saas/utils/encryption.py` — Fernet encrypt/decrypt
- [ ] Create `saas/api/deps.py` — `get_current_user` dependency
- [ ] Create `saas/api/v1/auth.py` endpoints:
  - `POST /auth/register`
  - `POST /auth/login`
  - `POST /auth/refresh`
  - `POST /auth/logout`
- [ ] On registration: create Stripe customer + free subscription
- [ ] Write auth tests (register, login, token refresh, invalid tokens)

#### P1-2: FastAPI App Setup
- [ ] Create `saas/main.py` — FastAPI app factory with lifespan
- [ ] Create `saas/middleware/cors.py` — CORS configuration
- [ ] Create `saas/middleware/rate_limit.py` — Redis-based rate limiting
- [ ] Create `saas/middleware/request_id.py` — Request ID injection
- [ ] Create `saas/api/v1/router.py` — aggregate all routers
- [ ] Create `saas/api/v1/health.py` — health check endpoint
- [ ] Verify: `uvicorn saas.main:app --reload` starts and serves OpenAPI docs

#### P1-3: Jobs API
- [ ] Create `saas/schemas/job.py` — Pydantic models for request/response
- [ ] Create `saas/services/job_service.py` — Job CRUD
- [ ] Create `saas/api/v1/jobs.py` endpoints:
  - `POST /jobs` — create job, enqueue to Celery
  - `GET /jobs` — list user's jobs (paginated)
  - `GET /jobs/{id}` — job detail with stages
  - `DELETE /jobs/{id}` — cancel job
  - `POST /jobs/{id}/retry` — retry failed job
- [ ] Create `saas/services/usage_service.py` — check limits before job creation
- [ ] Input validation: topic length, language, sanitize text
- [ ] Write job API tests

#### P1-4: Celery Worker
- [ ] Create `saas/workers/celery_app.py` — Celery configuration
- [ ] Create `saas/tasks/pipeline_task.py` — `run_video_pipeline` task
- [ ] Create `saas/services/key_service.py` — resolve API keys (platform vs BYOK)
- [ ] Worker startup: pre-load Whisper model
- [ ] Progress callback: update DB + publish to Redis pub/sub
- [ ] Job completion: update status, create Video record
- [ ] Job failure: update status, store error message
- [ ] Write Celery task tests (mock pipeline)

#### P1-5: WebSocket Progress
- [ ] Create `saas/websocket/manager.py` — Connection manager + Redis pub/sub
- [ ] Create `saas/websocket/job_progress.py` — `/ws/jobs/{job_id}` endpoint
- [ ] WebSocket auth via query param token
- [ ] Verify: create job via API, watch progress via WebSocket

#### P1-6: Basic Frontend (Dashboard Shell)
- [ ] Initialize Next.js project in `frontend/`
- [ ] Set up Tailwind CSS + shadcn/ui
- [ ] Create `frontend/src/lib/api.ts` — API client
- [ ] Create `frontend/src/lib/auth.ts` — auth context
- [ ] Create layout with sidebar navigation
- [ ] Pages:
  - `/login` — email/password login form
  - `/register` — registration form
  - `/dashboard` — dashboard home (job stats)
  - `/dashboard/jobs` — job list
  - `/dashboard/jobs/new` — create job form
  - `/dashboard/jobs/{id}` — job progress (WebSocket)
- [ ] Create `use-job-progress` hook (WebSocket)

**Deliverable:** Working end-to-end: register → login → create job → watch progress
→ see completed video. No billing, no YouTube upload yet.

---

## Phase 2: Billing & Storage (Week 6-7)

**Goal:** Stripe payments, S3 storage, plan enforcement.

### Tasks

#### P2-1: Stripe Integration
- [ ] Create Stripe products and prices (via script or dashboard)
- [ ] Create `saas/services/billing_service.py`:
  - `create_checkout_session()` — start subscription
  - `create_portal_session()` — self-service billing management
  - `record_usage()` — report metered overage
- [ ] Create `saas/api/v1/billing.py` endpoints:
  - `GET /billing/plans` — list plans
  - `GET /billing/subscription` — current subscription
  - `POST /billing/checkout` — create Checkout session
  - `POST /billing/portal` — create Customer Portal session
  - `GET /billing/invoices` — invoice history
- [ ] Create `saas/api/v1/webhooks.py`:
  - `POST /webhooks/stripe` — handle subscription events
  - Verify webhook signature
  - Handle: created, updated, deleted, payment_succeeded, payment_failed
- [ ] Update `usage_service.py` — enforce plan limits on job creation
- [ ] Free tier: 3 videos/month hard limit
- [ ] Paid tiers: allow overage with metered billing
- [ ] Write billing tests (mock Stripe)

#### P2-2: S3 Storage
- [ ] Create `saas/services/storage_service.py` — upload, download, delete, presigned URLs
- [ ] Update pipeline task: upload artifacts to S3 after completion
- [ ] Update Video model: store S3 keys and public URLs
- [ ] Create `GET /videos/{id}/download` — presigned download URL
- [ ] Free tier: videos expire after 7 days
- [ ] Paid tiers: videos persist indefinitely
- [ ] Create `saas/tasks/cleanup_task.py` — delete expired media

#### P2-3: BYOK (Bring Your Own Keys)
- [ ] Create `saas/api/v1/provider_keys.py` endpoints:
  - `GET /users/me/provider-keys`
  - `PUT /users/me/provider-keys/{provider}`
  - `DELETE /users/me/provider-keys/{provider}`
  - `POST /users/me/provider-keys/{provider}/verify`
- [ ] Encrypt keys with Fernet before storing in PostgreSQL
- [ ] Update `key_service.py`: check BYOK first, fallback to platform keys
- [ ] BYOK jobs get discounted overage pricing

#### P2-4: Frontend — Billing Pages
- [ ] `/dashboard/billing` — current plan, usage bar, invoices
- [ ] `/dashboard/billing/plans` — plan comparison, upgrade button
- [ ] `/dashboard/billing/success` — post-checkout success page
- [ ] `/dashboard/settings/provider-keys` — BYOK key management
- [ ] Usage warnings: toast when approaching limit

**Deliverable:** Users can subscribe, pay, and usage is enforced. Videos stored in S3.
BYOK support working.

---

## Phase 3: Teams & Channels (Week 8-10)

**Goal:** YouTube channel connections, team management, agency features.

### Tasks

#### P3-1: YouTube Channel Connection
- [ ] Create `saas/services/channel_service.py`:
  - YouTube OAuth flow (separate from user OAuth)
  - Token encryption and storage
  - Token refresh logic
- [ ] Create `saas/api/v1/channels.py` endpoints:
  - `GET /channels` — list connected channels
  - `POST /channels/connect` — start YouTube OAuth
  - `GET /channels/callback` — OAuth callback
  - `PATCH /channels/{id}` — update settings
  - `DELETE /channels/{id}` — disconnect
  - `POST /channels/{id}/verify` — test connection
- [ ] Update pipeline task: auto-upload to YouTube when `auto_upload=true`
- [ ] Channel limit enforcement per plan
- [ ] Frontend: channel management page, connect flow

#### P3-2: Team Management
- [ ] Create `saas/services/team_service.py`:
  - Team CRUD
  - Member invite/accept/remove
  - Role-based permission checks
- [ ] Create `saas/api/v1/teams.py` endpoints (all from 10-agency-features.md):
  - Team CRUD
  - Member management
  - Team jobs list
  - Team channels
  - Team usage analytics
  - Team calendar
- [ ] Update job/video queries: support team context
- [ ] Update channel model: optional team assignment
- [ ] Team seat limit enforcement

#### P3-3: Agency Frontend
- [ ] `/dashboard/teams` — team list
- [ ] `/dashboard/teams/{id}` — team dashboard
- [ ] `/dashboard/teams/{id}/members` — member list + invite
- [ ] `/dashboard/teams/{id}/channels` — shared channels
- [ ] `/dashboard/teams/{id}/calendar` — content calendar
- [ ] `/dashboard/teams/{id}/usage` — team analytics
- [ ] Team switcher in sidebar
- [ ] Bulk job creation (`POST /jobs/bulk`)

#### P3-4: Trending Topics
- [ ] Create `saas/tasks/topic_task.py` — periodic topic refresh
- [ ] Create `saas/api/v1/topics.py` endpoints:
  - `GET /topics/trending` — cached topics
  - `POST /topics/quick-create` — one-click video from topic
- [ ] Frontend: trending topics page with "Create Video" buttons
- [ ] Celery Beat: refresh every 15 minutes
- [ ] Feature-gate: trending topics only on Creator+ plans

#### P3-5: Social Login
- [ ] Google OAuth login (`/auth/google`, `/auth/google/callback`)
- [ ] GitHub OAuth login (`/auth/github`, `/auth/github/callback`)
- [ ] Link OAuth to existing account
- [ ] Frontend: social login buttons on register/login pages

**Deliverable:** Full agency workflow working. Teams can share channels, create videos
together, and view analytics. YouTube auto-upload functional. Social login active.

---

## Phase 4: Polish & Launch (Week 11-12)

**Goal:** Production-ready with monitoring, landing page, and launch prep.

### Tasks

#### P4-1: Monitoring & Observability
- [ ] Sentry integration (API + workers)
- [ ] Health check endpoint (`/health`)
- [ ] Celery Flower dashboard
- [ ] Prometheus metrics (job success rate, duration, cost)
- [ ] Log aggregation setup
- [ ] Alert rules (job failure rate > 5%, worker count < 2, etc.)

#### P4-2: Landing Page (see [08a-visual-design.md](../saas-plan/08a-visual-design.md))
- [ ] Set up R3F hero scene with GSAP ScrollTrigger (dynamic import, SSR disabled)
- [ ] Create 3D pipeline visualization geometry + post-processing (bloom, chromatic aberration)
- [ ] Build hero fallback component (CSS mesh gradient for mobile + loading state)
- [ ] Create Rive animations for 8 pipeline stage icons (.riv files, ~10-30KB each)
- [ ] Build "How it works" section with Rive icons + gradient SVG connecting line
- [ ] Build glassmorphic feature cards with CSS perspective tilt on hover
- [ ] Build live stats section with spring-animated counters
- [ ] Build pricing section with staggered perspective entrance + animated gradient border
- [ ] Build CTA section with CSS mesh gradient background
- [ ] Performance budget testing: Lighthouse (LCP < 2.5s), `@next/bundle-analyzer` (Three.js isolated in own chunk, <250KB)
- [ ] Mobile testing: verify CSS fallback on mobile, no WebGL loaded
- [ ] SEO optimization (meta tags, OpenGraph, structured data)

#### P4-3: Admin Dashboard
- [ ] `/admin` — system stats (users, jobs, revenue, costs)
- [ ] `/admin/users` — user management (search, ban, change plan)
- [ ] `/admin/jobs` — global job view (filter by status, user)
- [ ] Admin-only API endpoints with role check

#### P4-4: Email Notifications
- [ ] Set up transactional email (Resend, Postmark, or SendGrid)
- [ ] Email templates:
  - Welcome email (after registration)
  - Job completed (with video preview)
  - Job failed (with error + retry link)
  - Team invite
  - Payment failed warning
  - Usage limit approaching (80%, 100%)
- [ ] Unsubscribe preferences

#### P4-5: Documentation
- [ ] API documentation (auto-generated OpenAPI + examples)
- [ ] Getting started guide for new users
- [ ] API key guide for programmatic access
- [ ] Agency setup guide
- [ ] FAQ / troubleshooting

#### P4-6: Security Hardening
- [ ] Security audit of all endpoints
- [ ] Input validation on all user-facing fields
- [ ] Rate limiting tuned per tier
- [ ] CSRF protection on auth endpoints
- [ ] Content Security Policy headers
- [ ] Dependency vulnerability scan

#### P4-7: Production Deployment
- [ ] Set up Railway (or chosen platform) with all services
- [ ] Configure custom domain + SSL
- [ ] Set up Cloudflare R2 bucket + CDN
- [ ] Configure Stripe webhooks for production
- [ ] Set up YouTube OAuth for production (Google Cloud project)
- [ ] Database backups configured
- [ ] Staging environment for pre-launch testing

**Deliverable:** Production deployment live. Landing page published. Monitoring active.
Ready for users.

---

## Phase 4.5: Remaining Fixes & Feature Completeness (Week 12-13)

**Goal:** Fix all bugs, implement all missing spec endpoints, harden security.

See **[13-remaining-features.md](13-remaining-features.md)** for the full execution brief
with 35 items across 4 sub-phases:

- **Phase A (Critical):** Celery Beat schedule, admin stats fix, rate limiting, Alembic
  migrations, PATCH privilege escalation, usage record crash, SSE keepalive
- **Phase B (Endpoints):** Password reset, email verification, user usage/API keys,
  billing invoices, YouTube upload, topic refresh, admin jobs, team channels/invites
- **Phase C (Quality):** JWT blacklist, webhook idempotency, error standardization,
  pagination consistency, exception narrowing, DRY extraction, indexes, dep pinning
- **Phase D (Infra):** Docker full stack, scheduled jobs, email service, admin
  dashboard data, audit logging, team role fix

---

## Phase 5: Growth (Week 14+)

**Goal:** Advanced features, optimization, scale based on user feedback.

### Feature Backlog (Prioritize Based on User Demand)

#### High Priority
- [ ] Caption style templates (TikTok style, news style, educational, minimal)
- [ ] Voice selection marketplace (browse ElevenLabs voices)
- [ ] Music genre selection with preview
- [ ] Video preview before YouTube upload
- [ ] Batch scheduling (create content calendar for the month)
- [ ] Video performance analytics (YouTube API integration for view counts)

#### Medium Priority
- [ ] A/B testing for thumbnails (generate 2, upload both, track performance)
- [ ] Multi-language support (add Spanish, Portuguese, French, German, Japanese)
- [ ] Custom thumbnail upload (skip AI generation)
- [ ] Script editing before production (approve/edit Claude's script)
- [ ] Template system (save and reuse style configurations)
- [ ] Webhook notifications (POST to user's URL on job completion)

#### Lower Priority
- [ ] Mobile app (React Native)
- [ ] Slack integration (create videos from Slack)
- [ ] Zapier/Make integration
- [ ] White-label API (agency customers resell the service)
- [ ] Video repurposing (Long video → multiple Shorts)
- [ ] Instagram Reels / TikTok direct upload

#### Infrastructure
- [ ] Switch from openai-whisper to faster-whisper (4x speedup)
- [ ] GPU workers for Whisper (8x speedup)
- [ ] Hardware-accelerated ffmpeg encoding (NVENC)
- [ ] Parallel broll + voiceover (independent stages)
- [ ] CDN cache warming for popular videos
- [ ] Database read replicas
- [ ] Kubernetes migration (if traffic justifies)

---

## Success Metrics

### Launch (Week 12)
- [ ] 100 registered users
- [ ] 10 paying customers
- [ ] 95% job success rate
- [ ] < 5 min average job duration
- [ ] < $0.15 average cost per video

### Month 3 (Week 24)
- [ ] 1,000 registered users
- [ ] 100 paying customers
- [ ] $3,000+ MRR
- [ ] 3+ agency customers
- [ ] < 3 min average job duration

### Month 6 (Week 36)
- [ ] 5,000 registered users
- [ ] 500 paying customers
- [ ] $15,000+ MRR
- [ ] 10+ agency customers
- [ ] API marketplace integrations

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| YouTube API quota limits (10K units/day) | Can't upload videos | Apply for higher quota; batch uploads during off-peak |
| ElevenLabs rate limiting | Voiceover failures | BYOK keys; queue-based rate limiting; fallback TTS |
| Gemini API changes/pricing | B-roll generation breaks | Abstract image generation; add DALL-E/Flux fallback |
| Whisper CPU bottleneck | Slow captions | faster-whisper migration; GPU workers; pre-compute |
| Stripe integration complexity | Billing bugs | Extensive webhook testing; use Stripe test mode |
| YouTube TOS violations | Account bans | Content screening; default to private; user acknowledgment |
| API cost spikes | Negative margins | Usage-based billing; hard limits on free tier; BYOK |
| Security breach | User data leak | Encryption at rest; pen testing; audit logs |
