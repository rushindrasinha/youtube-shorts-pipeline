# 13 — Remaining Work: Bugs, Missing Features, Quality & Completeness

> **35 items** found by exhaustive code audit. Organized into 4 execution phases
> with exact file paths, code fixes, and verification steps. Each item is an
> independent work unit assignable to an agent.

---

## Phase A: Critical Fixes (7 items)

These are bugs or security issues that must be fixed before any deployment.

---

### A1. Celery Beat schedule not configured

**File:** `apps/api/saas/workers/celery_app.py`
**Issue:** Tasks `refresh_trending_topics` and `cleanup_expired_media` are defined
but never scheduled. Trending topics never refresh. Expired free-tier videos are
never deleted.

**Fix:** Add after `app.config_from_object(...)`:
```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    "refresh-trending-topics": {
        "task": "saas.tasks.topic_task.refresh_trending_topics",
        "schedule": crontab(minute="*/15"),
    },
    "cleanup-expired-media": {
        "task": "saas.tasks.cleanup_task.cleanup_expired_media",
        "schedule": crontab(hour=2, minute=0),
    },
}
```

**Verify:** `celery -A saas.workers.celery_app inspect scheduled` shows 2 entries.

---

### A2. Admin stats broken SQL — sums IDs not revenue

**File:** `apps/api/saas/api/v1/admin.py` ~line 37
**Issue:** `func.sum(Subscription.id)` sums UUID primary keys instead of revenue.

**Fix:** Replace with:
```python
total_cost = db.query(func.sum(Job.cost_usd)).filter(Job.status == "completed").scalar() or 0
```

**Verify:** `GET /admin/stats` returns sensible `total_revenue` value.

---

### A3. Rate limiting not implemented

**Files:** `apps/api/saas/main.py`, new `apps/api/saas/middleware/rate_limit.py`
**Issue:** No rate limiting on any endpoint. API spec defines per-tier limits.
**Deps:** `slowapi` package (add to `requirements-saas.txt`)

**Fix:** Create rate limiter middleware:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)

# In main.py:
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# On auth endpoints:
@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...): ...
```

**Verify:** 6th login attempt within 1 minute returns 429.

---

### A4. Alembic migration files not generated

**File:** `apps/api/migrations/versions/` — only `.gitkeep`
**Issue:** Schema exists in models but no migration SQL generated.

**Fix:**
```bash
cd apps/api
alembic revision --autogenerate -m "initial_schema"
# Then create seed migration for plans:
alembic revision -m "seed_plans"
# In the seed migration, insert the 5 plans from 03-database-schema.md
```

**Verify:** `alembic upgrade head` creates all tables. `alembic current` shows head.

---

### A5. User PATCH privilege escalation

**File:** `apps/api/saas/api/v1/users.py` ~line 42-53
**Issue:** `PATCH /users/me` accepts any field and sets it via `setattr()`.
A user can send `{"role": "admin"}` to elevate privileges.

**Fix:** Whitelist allowed fields in `UpdateUserRequest`:
```python
class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    default_lang: str | None = None
    caption_style: str | None = None
    music_genre: str | None = None
    # NO role, is_active, email, password_hash — these are admin-only
```
And in the endpoint, only update whitelisted fields:
```python
ALLOWED_FIELDS = {"display_name", "default_lang", "caption_style", "music_genre"}
for field, value in update_data.items():
    if field in ALLOWED_FIELDS:
        setattr(user, field, value)
```

**Verify:** `PATCH /users/me {"role": "admin"}` does NOT change role.

---

### A6. Usage record crash on month rollover

**File:** `apps/api/saas/services/usage_service.py`
**Issue:** `check_can_create_job` calls `with_for_update()` but if no UsageRecord
exists for the current period (new month), query returns `None` and subsequent
code crashes.

**Fix:** Add get-or-create pattern:
```python
usage = db.query(UsageRecord).filter(...).with_for_update().first()
if not usage:
    usage = UsageRecord(user_id=user.id, period_start=period_start, ...)
    db.add(usage)
    db.flush()
```

**Verify:** Create job on first day of new month without prior usage record.

---

### A7. SSE keepalive missing

**File:** `apps/api/saas/api/v1/jobs.py` — SSE endpoint
**Issue:** Long-lived SSE connections timeout on proxies/CDNs without keepalive.

**Fix:** Add keepalive comment every 15 seconds:
```python
async def event_stream():
    ...
    import asyncio
    last_keepalive = time.time()
    async for message in pubsub.listen():
        if time.time() - last_keepalive > 15:
            yield ": keepalive\n\n"
            last_keepalive = time.time()
        # ... existing message handling
```

**Verify:** SSE connection stays open for >1 minute behind nginx.

---

## Phase B: Missing Endpoints (12 items)

These are endpoints defined in `04-api-design.md` but not implemented.

---

### B1. Password reset flow

**Files:** `apps/api/saas/api/v1/auth.py`, `apps/api/saas/services/auth_service.py`
**Endpoints:**
- `POST /auth/forgot-password` — accept email, generate reset token (JWT, 1h expiry), send email
- `POST /auth/reset-password` — accept token + new password, update hash

**Implementation:**
```python
def create_password_reset_token(email: str) -> str:
    return jwt.encode({"sub": email, "type": "password_reset", "exp": now + 1h}, SECRET_KEY)

@router.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db = ...):
    user = db.query(User).filter(User.email == body.email).first()
    if user:  # Don't reveal if email exists
        token = create_password_reset_token(user.email)
        # TODO: send email with reset link
    return {"status": "ok"}  # Always return ok

@router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest, db = ...):
    payload = verify_token(body.token)
    if payload.get("type") != "password_reset":
        raise HTTPException(400)
    user = db.query(User).filter(User.email == payload["sub"]).first()
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"status": "ok"}
```

---

### B2. Email verification

**Files:** `apps/api/saas/api/v1/auth.py`, `apps/api/saas/services/auth_service.py`
**Endpoint:** `POST /auth/verify-email`

**Implementation:**
- On register: generate verification token, send email
- Endpoint: accept token, set `email_verified=True`
- Optionally: block job creation until email verified

---

### B3. GET /users/me/usage

**File:** `apps/api/saas/api/v1/users.py`
**Spec ref:** 04-api-design.md lines 138-154

```python
@router.get("/users/me/usage")
def get_my_usage(user = Depends(get_current_user), db = Depends(get_db)):
    usage = usage_service.get_current_usage(user)
    return {
        "period_start": usage.period_start,
        "period_end": usage.period_end,
        "videos_created": usage.videos_created,
        "videos_limit": usage.videos_limit,
        "overage_count": usage.overage_count,
    }
```

---

### B4. GET/POST/DELETE /users/me/api-keys

**File:** `apps/api/saas/api/v1/users.py`
**Model:** `UserAPIKey` (already exists)

```python
@router.get("/users/me/api-keys")
def list_api_keys(user = ..., db = ...):
    return db.query(UserAPIKey).filter(UserAPIKey.user_id == user.id, UserAPIKey.is_active).all()

@router.post("/users/me/api-keys", status_code=201)
def create_api_key(body: CreateAPIKeyRequest, user = ..., db = ...):
    import secrets, hashlib
    raw_key = f"sf_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    record = UserAPIKey(user_id=user.id, name=body.name, key_prefix=raw_key[:8], key_hash=key_hash)
    db.add(record)
    db.commit()
    return {"key": raw_key, "id": record.id}  # Only time full key is shown

@router.delete("/users/me/api-keys/{key_id}")
def revoke_api_key(key_id: UUID, user = ..., db = ...):
    key = db.query(UserAPIKey).filter(UserAPIKey.id == key_id, UserAPIKey.user_id == user.id).first()
    if not key: raise HTTPException(404)
    key.is_active = False
    db.commit()
```

---

### B5. GET /billing/invoices

**File:** `apps/api/saas/api/v1/billing.py`

```python
@router.get("/billing/invoices")
def list_invoices(user = ..., db = ...):
    if not user.stripe_customer_id:
        return {"invoices": []}
    invoices = stripe.Invoice.list(customer=user.stripe_customer_id, limit=20)
    return {"invoices": [{"id": i.id, "amount": i.total, "status": i.status, "date": i.created} for i in invoices.data]}
```

---

### B6. POST /videos/{id}/upload-youtube

**File:** `apps/api/saas/api/v1/videos.py`

```python
@router.post("/videos/{video_id}/upload-youtube")
def upload_video_to_youtube(video_id: UUID, body: UploadYouTubeRequest, user = ..., db = ...):
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == user.id).first()
    channel = db.query(YouTubeChannel).filter(YouTubeChannel.id == body.channel_id).first()
    # Verify access, enqueue Celery task
    upload_to_youtube_task.delay(str(video.id), str(channel.id))
    return {"status": "uploading"}
```

---

### B7. POST /topics/refresh

**File:** `apps/api/saas/api/v1/topics.py`

```python
@router.post("/topics/refresh")
def refresh_topics(user = Depends(get_current_user)):
    from saas.tasks.topic_task import refresh_trending_topics
    refresh_trending_topics.delay()
    return {"status": "refreshing"}
```

---

### B8. GET /admin/jobs + GET /admin/system

**File:** `apps/api/saas/api/v1/admin.py`

```python
@router.get("/admin/jobs")
def list_all_jobs(status: str = None, limit: int = 50, offset: int = 0, user = ..., db = ...):
    if user.role != "admin": raise HTTPException(403)
    query = db.query(Job)
    if status: query = query.filter(Job.status == status)
    return query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/admin/system")
def system_health(user = ..., db = ...):
    if user.role != "admin": raise HTTPException(403)
    # DB check, Redis check, Celery worker count, queue depths
```

---

### B9. GET /teams/{id}/channels

**File:** `apps/api/saas/api/v1/teams.py`

```python
@router.get("/teams/{team_id}/channels")
def list_team_channels(team_id: UUID, user = ..., db = ...):
    # Verify user is team member
    channels = db.query(YouTubeChannel).filter(YouTubeChannel.team_id == team_id).all()
    return channels
```

---

### B10. POST /teams/invites/{token}/accept

**File:** `apps/api/saas/api/v1/teams.py`

```python
@router.post("/teams/invites/{token}/accept")
def accept_invite(token: str, user = ..., db = ...):
    invite = db.query(TeamInvite).filter(TeamInvite.token == token, TeamInvite.accepted_at.is_(None)).first()
    if not invite or invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Invalid or expired invite")
    member = TeamMember(team_id=invite.team_id, user_id=user.id, role=invite.role)
    db.add(member)
    invite.accepted_at = datetime.now(timezone.utc)
    db.commit()
    return {"team_id": str(invite.team_id), "role": invite.role}
```

---

## Phase C: Quality & Security Hardening (10 items)

---

### C1. JWT token blacklist

**Files:** `apps/api/saas/services/auth_service.py`, `apps/api/saas/api/deps.py`
**Fix:** On logout, add JTI to Redis set with TTL. In `verify_token()`, check JTI
is not in blacklist.

### C2. Stripe webhook idempotency

**File:** `apps/api/saas/api/v1/webhooks.py`
**Fix:** Store `event.id` in Redis. If already processed, return 200 immediately.

### C3. Standardize error responses

**Files:** All endpoint files
**Fix:** Create FastAPI exception handler that wraps all HTTPExceptions in
`{"error": {"code": "...", "message": "...", "details": {...}}}` format.

### C4. Standardize pagination

**Files:** `admin.py` (offset), `teams.py` (no pagination on members)
**Fix:** Convert all list endpoints to cursor-based pagination.

### C5. Narrow exception blocks

**Files:** `jobs.py:71,158,212`, `channel_service.py:170`, `provider_keys.py:291`
**Fix:** Replace `except Exception` with specific exceptions.

### C6. Extract `_build_user_response`

**Files:** `auth.py`, `users.py`
**Fix:** Move to `apps/api/saas/schemas/auth.py` as a classmethod on `UserResponse`.

### C7. Stage names to constants

**Files:** `job_service.py`, `pipeline_task.py`
**Fix:** Create `apps/api/saas/constants.py` with `PIPELINE_STAGES` list.

### C8. Add missing database indexes

**Files:** Model files
**Fix:** Add `Index("idx_videos_user_created", "user_id", "created_at")`, etc.

### C9. Pin dependency upper bounds

**File:** `requirements.txt`, `requirements-saas.txt`
**Fix:** Add `<2.0` bounds to `faster-whisper`, `uvicorn`, `asyncpg`, `psycopg2-binary`.

### C10. Re-check quota on job retry

**File:** `apps/api/saas/api/v1/jobs.py` (retry endpoint)
**Fix:** Call `usage_service.check_can_create_job()` before re-enqueueing.

---

## Phase D: Infrastructure & Integration (6 items)

---

### D1. Docker compose: full dev stack

**File:** `docker/docker-compose.yml`
**Fix:** Add `api`, `worker`, `beat` services alongside postgres and redis.

### D2. Scheduled job execution

**File:** New `apps/api/saas/tasks/scheduler_task.py`
**Fix:** Celery Beat task that queries jobs with `scheduled_at <= now()` and
`status = 'queued'`, then dispatches them to the pipeline task.

### D3. Email notification service

**Files:** New `apps/api/saas/services/email_service.py`
**Deps:** `resend` package
**Fix:** Create templates for: welcome, job complete, job failed, team invite,
payment failed, usage warning. Send via Resend API.

### D4. Admin dashboard: real data

**File:** `apps/web/src/app/admin/page.tsx`
**Fix:** Replace placeholder data with `useEffect` → `api.admin.stats()` call.
Add loading state and error handling.

### D5. Audit logging

**Files:** `apps/api/saas/api/v1/admin.py`, new `apps/api/saas/services/audit_service.py`
**Fix:** Log all admin actions (user ban, plan change) to `AuditLog` table.

### D6. Team role hierarchy fix

**File:** `apps/api/saas/services/team_service.py` ~line 229
**Fix:** Change `>=` to `>` so admins cannot promote to admin (only owner can).

---

## Execution Strategy

| Phase | Items | Agents | Parallel? |
|-------|-------|--------|-----------|
| **A** | 7 critical fixes | 2 agents | Yes (backend + infra) |
| **B** | 12 missing endpoints | 3 agents | Yes (auth, user/billing, teams/videos) |
| **C** | 10 quality items | 2 agents | Yes (security + code quality) |
| **D** | 6 infra items | 2 agents | Yes (docker/tasks + frontend/email) |

Total: ~9 agents across 4 phases, can run 2-3 per batch.
