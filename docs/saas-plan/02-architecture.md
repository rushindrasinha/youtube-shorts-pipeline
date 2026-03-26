# 02 — SaaS Architecture

## Technology Stack

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| **Backend API** | FastAPI | 0.110+ | Async-native, auto OpenAPI, Pydantic validation, WebSocket support |
| **Task Queue** | Celery | 5.3+ | Battle-tested, priority queues, result backend, monitoring |
| **Message Broker** | Redis | 7+ | Fast, Celery broker + result backend + caching + pub/sub for WebSocket |
| **Database** | PostgreSQL | 16+ | ACID, JSONB for flexible metadata, full-text search, scales for years |
| **ORM** | SQLAlchemy 2.0 | 2.0+ | Async support, Alembic migrations, mature ecosystem |
| **Migrations** | Alembic | 1.13+ | Industry standard for SQLAlchemy, auto-generates migrations |
| **Frontend** | Next.js | 15+ | App Router, SSR, Vercel deployment, shadcn/ui |
| **UI Components** | shadcn/ui + Tailwind | Latest | Beautiful, accessible, copy-paste components |
| **3D / Hero** | React Three Fiber + drei + postprocessing | 8.x / 9.x / 2.x | One cinematic 3D landing hero scene (see [08a-visual-design](08a-visual-design.md)) |
| **Scroll Animation** | GSAP + ScrollTrigger | 3.12+ | Scroll-driven 3D scene + section transitions |
| **UI Animation** | Framer Motion | 11+ | Page transitions, element entrances, hover states |
| **Micro-interactions** | Rive | Latest | Interactive pipeline stage icons, loading states |
| **Charts** | Tremor | 3.x | Usage/analytics charts, built on Tailwind |
| **Monorepo** | Turborepo + pnpm | Latest | Unified task orchestration, remote caching |
| **Object Storage** | S3-compatible (Cloudflare R2) | N/A | Zero egress fees, S3 API compatible, cheap storage |
| **CDN** | Cloudflare | N/A | Free tier generous, paired with R2 |
| **Auth** | JWT (httpOnly cookies) + OAuth2 | N/A | Secure token storage, social login, API keys for programmatic access |
| **Primary Keys** | UUIDv7 | N/A | Time-ordered (no B-tree index fragmentation), standard UUID type |
| **Real-time** | SSE (job progress) + WebSocket (notifications) | N/A | SSE: simpler, auto-reconnect, CDN-friendly for unidirectional updates |
| **Payments** | Stripe | Latest | Subscriptions + usage-based billing + webhooks |
| **Monitoring** | Sentry + Prometheus | N/A | Error tracking + metrics |
| **Deployment** | Docker + Railway | N/A | Simple to start, easy to migrate to k8s |
| **CI/CD** | GitHub Actions | N/A | Free for public repos, easy Docker builds |

### Why FastAPI over Django

| Factor | FastAPI | Django |
|--------|---------|--------|
| Async support | Native, built on Starlette | Bolt-on, limited |
| WebSocket | Built-in | Requires Channels (complex) |
| API documentation | Auto-generated OpenAPI/Swagger | DRF adds it but verbose |
| Validation | Pydantic (typed, fast) | Serializers (more boilerplate) |
| Performance | 3-5x faster request handling | Slower due to middleware stack |
| Learning curve | Small, focused API | Large framework, more opinions |
| Video generation API | Perfect fit (API-first) | Over-engineered for this |

Django's admin panel is nice but we'll build a custom dashboard anyway. FastAPI's
async WebSocket support and auto-documentation make it the clear winner.

---

## Directory Structure

```
youtube-shorts-pipeline/
  pipeline/                          # EXISTING — modified minimally
    __init__.py
    __main__.py                      # CLI preserved for local dev/testing
    adapter.py                       # NEW: SaaS-callable interface wrapping all stages
    config.py                        # MODIFIED: accept injected config dict
    state.py                         # MODIFIED: emit progress callbacks
    draft.py                         # MODIFIED: accept API client injection
    broll.py                         # MODIFIED: parallel generation, storage backend
    voiceover.py
    captions.py                      # MODIFIED: use faster-whisper, cache model
    music.py                         # MODIFIED: genre selection support
    assemble.py
    thumbnail.py
    upload.py                        # MODIFIED: accept OAuth credentials injection
    research.py
    retry.py
    log.py
    topics/
  saas/                              # NEW — SaaS application
    __init__.py
    main.py                          # FastAPI app factory + lifespan
    settings.py                      # Pydantic Settings (env vars)
    api/
      __init__.py
      deps.py                        # Dependency injection (get_db, get_user, etc.)
      v1/
        __init__.py
        router.py                    # Aggregates all v1 routers
        auth.py                      # POST /auth/register, /auth/login, /auth/google, etc.
        users.py                     # GET/PATCH /users/me, GET /users/me/usage
        jobs.py                      # POST /jobs, GET /jobs, GET /jobs/{id}, DELETE /jobs/{id}
        videos.py                    # GET /videos, GET /videos/{id}, GET /videos/{id}/download
        topics.py                    # GET /topics/trending, POST /topics/refresh
        channels.py                  # CRUD /channels (YouTube channel connections)
        teams.py                     # CRUD /teams, /teams/{id}/members (Agency feature)
        billing.py                   # GET /billing, POST /billing/checkout, webhooks
        admin.py                     # Admin-only endpoints (user management, system stats)
        webhooks.py                  # POST /webhooks/stripe
    models/
      __init__.py
      user.py                        # User, UserAPIKey, OAuthConnection
      team.py                        # Team, TeamMember, TeamInvite
      job.py                         # Job, JobStage
      video.py                       # Video, VideoAnalytics
      channel.py                     # YouTubeChannel (OAuth tokens)
      subscription.py                # Subscription, Plan, UsageRecord
      api_keys.py                    # UserProviderKey (encrypted BYOK storage)
    schemas/
      __init__.py
      auth.py                        # RegisterRequest, LoginRequest, TokenResponse
      job.py                         # JobCreate, JobResponse, JobProgress
      video.py                       # VideoResponse, VideoListResponse
      topic.py                       # TopicResponse, TopicListResponse
      channel.py                     # ChannelCreate, ChannelResponse
      team.py                        # TeamCreate, TeamResponse, InviteRequest
      billing.py                     # PlanResponse, CheckoutRequest, UsageResponse
      common.py                      # PaginatedResponse, ErrorResponse
    services/
      __init__.py
      auth_service.py                # JWT creation, password hashing, OAuth flow
      job_service.py                 # Job CRUD, status tracking
      video_service.py               # Video metadata, download URLs
      billing_service.py             # Stripe customer/subscription management
      key_service.py                 # API key encryption/decryption, BYOK management
      storage_service.py             # S3 upload/download/presigned URLs
      channel_service.py             # YouTube OAuth flow, token management
      topic_service.py               # Trending topic caching and discovery
      team_service.py                # Team CRUD, member management, permissions
      usage_service.py               # Usage tracking, limit enforcement
      notification_service.py        # Email notifications (job complete, limit warnings)
    tasks/
      __init__.py
      pipeline_task.py               # Main Celery task: runs full pipeline for a job
      stage_tasks.py                 # Individual stage tasks (for future fine-grained control)
      cleanup_task.py                # Periodic: delete expired media files
      billing_task.py                # Periodic: sync usage with Stripe meters
      topic_task.py                  # Periodic: refresh trending topics cache
    workers/
      __init__.py
      celery_app.py                  # Celery app configuration
      worker_init.py                 # Worker startup: load Whisper model, warm caches
    middleware/
      __init__.py
      rate_limit.py                  # Per-user rate limiting via Redis
      cors.py                        # CORS configuration
      request_id.py                  # Request ID injection for tracing
    utils/
      __init__.py
      encryption.py                  # Fernet encryption for API keys and OAuth tokens
      pagination.py                  # Cursor-based pagination helpers
      validators.py                  # Input validation (topic text, etc.)
    websocket/
      __init__.py
      manager.py                     # WebSocket connection manager
      job_progress.py                # Job progress WebSocket endpoint
    migrations/
      env.py                         # Alembic environment
      versions/                      # Migration scripts
  frontend/                          # NEW — Next.js application
    (see 08-frontend.md)
  docker/
    Dockerfile.api                   # FastAPI + Uvicorn
    Dockerfile.worker                # Celery worker + ffmpeg + Whisper
    docker-compose.yml               # Full local dev stack
    docker-compose.prod.yml          # Production overrides
  tests/                             # EXISTING — extended
    pipeline/                        # Existing pipeline tests (moved)
    saas/                            # New SaaS tests
      test_auth.py
      test_jobs.py
      test_billing.py
      test_teams.py
      test_pipeline_adapter.py
      conftest.py                    # Test fixtures (test DB, mock Redis, etc.)
  docs/
    saas-plan/                       # This plan directory
  alembic.ini                        # Alembic configuration
  pyproject.toml                     # MODIFIED: add SaaS dependencies
  requirements.txt                   # MODIFIED: add SaaS dependencies
  requirements-saas.txt              # NEW: SaaS-specific dependencies
  .env.example                       # NEW: environment variable template
```

---

## Request Flow

### Video Generation (Happy Path)

```
1. User → POST /api/v1/jobs {topic: "...", channel_id: "..."}
2. API validates input, checks subscription limits
3. API creates Job record (status=QUEUED) in PostgreSQL
4. API publishes job to Celery via Redis
5. API returns 202 Accepted {job_id, status: "queued"}
6. User connects to WebSocket /ws/jobs/{job_id}

7. Celery worker picks up job
8. Worker calls pipeline.adapter.run_pipeline(config)
9. For each stage:
   a. Adapter calls stage function with injected config
   b. Adapter emits progress event via Redis pub/sub
   c. WebSocket manager broadcasts to connected clients
   d. Worker updates Job record in PostgreSQL

10. On completion:
    a. Worker uploads final video + thumbnail to S3
    b. Worker updates Job status to COMPLETED
    c. Worker creates Video record with S3 URLs
    d. Worker increments user's usage counter
    e. If auto-upload enabled: uploads to YouTube via user's OAuth
    f. WebSocket sends final event with video URL

11. User sees video in dashboard, can download or manage
```

### Authentication Flow

```
1. User → POST /auth/register {email, password}
   OR
   User → GET /auth/google (redirect to Google OAuth)

2. API creates User record
3. API creates Stripe customer
4. API returns JWT access token + refresh token

5. All subsequent requests include: Authorization: Bearer <jwt>
6. API middleware validates JWT, injects user into request
```

### Stripe Webhook Flow

```
1. Stripe → POST /webhooks/stripe {event}
2. API validates webhook signature
3. Switch on event type:
   - customer.subscription.created → activate plan
   - customer.subscription.updated → update plan limits
   - customer.subscription.deleted → downgrade to free
   - invoice.payment_succeeded → record payment
   - invoice.payment_failed → notify user, grace period
```

---

## Multi-Tenancy Model

### Data Isolation Strategy: Shared Database, Row-Level Isolation

Every table includes `user_id` (or `team_id` for agency features). All queries
filter by the authenticated user's ID. No cross-tenant data access is possible
via the API.

```python
# Every query automatically scoped to current user
@router.get("/jobs")
async def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Job).filter(Job.user_id == user.id).all()
```

### API Key Isolation

| Key Type | Storage | Isolation |
|----------|---------|-----------|
| Platform API keys | Environment variables on workers | Shared across all users |
| BYOK API keys | PostgreSQL, Fernet-encrypted per-user | Decrypted only during job execution |
| YouTube OAuth tokens | PostgreSQL, Fernet-encrypted per-channel | Decrypted only during upload |
| User API keys (for our API) | PostgreSQL, hashed with prefix | User generates via dashboard |

### Storage Isolation

S3 paths follow a strict user-scoped pattern:
```
s3://shortfactory-media/{user_id}/{YYYY-MM}/{job_id}/broll_0.png
s3://shortfactory-media/{user_id}/{YYYY-MM}/{job_id}/voiceover.mp3
s3://shortfactory-media/{user_id}/{YYYY-MM}/{job_id}/final.mp4
s3://shortfactory-media/{user_id}/{YYYY-MM}/{job_id}/thumbnail.png
```

No user can ever access another user's storage prefix.

---

## Scaling Strategy

### Phase 1: Single Server (0-1K users)

- 1x API server (FastAPI + Uvicorn, 4 workers)
- 1x Celery worker (4 concurrent tasks)
- 1x PostgreSQL instance
- 1x Redis instance
- S3 for media storage

### Phase 2: Horizontal Workers (1K-10K users)

- 2x API servers behind load balancer
- 4-8x Celery workers (auto-scaled based on queue depth)
- 1x PostgreSQL (upgraded instance)
- 1x Redis cluster
- GPU worker instances for Whisper acceleration

### Phase 3: Full Scale (10K+ users)

- Kubernetes cluster
- Auto-scaling worker pools by job type
- PostgreSQL read replicas
- Redis Cluster
- Dedicated GPU nodes for Whisper
- CDN for video delivery
- Regional deployment for latency
