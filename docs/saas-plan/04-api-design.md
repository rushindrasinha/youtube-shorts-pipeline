# 04 — REST API Design

## Base URL

```
Production:  https://api.shortfactory.io/v1
Development: http://localhost:8000/api/v1
```

## Authentication

All endpoints except `/auth/*` and `/webhooks/*` require a Bearer token:
```
Authorization: Bearer <jwt_access_token>
```

Or an API key (for programmatic access):
```
X-API-Key: sf_live_xxxxxxxxxxxxxxxxxxxx
```

---

## Endpoints

### Auth — `/auth`

```
POST   /auth/register              Register with email + password
POST   /auth/login                 Login, returns JWT tokens
POST   /auth/refresh               Refresh access token
POST   /auth/logout                Invalidate refresh token
GET    /auth/google                Redirect to Google OAuth
GET    /auth/google/callback       Google OAuth callback
GET    /auth/github                Redirect to GitHub OAuth
GET    /auth/github/callback       GitHub OAuth callback
POST   /auth/forgot-password       Send password reset email
POST   /auth/reset-password        Reset password with token
POST   /auth/verify-email          Verify email with token
```

#### POST /auth/register

```json
// Request
{
  "email": "user@example.com",
  "password": "securepassword",
  "display_name": "John Doe"
}

// Response 201
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "John Doe",
    "role": "user"
  },
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600
}
```

#### POST /auth/login

```json
// Request
{
  "email": "user@example.com",
  "password": "securepassword"
}

// Response 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600
}
```

---

### Users — `/users`

```
GET    /users/me                   Get current user profile
PATCH  /users/me                   Update profile and preferences
GET    /users/me/usage             Get current billing period usage
GET    /users/me/api-keys          List API keys
POST   /users/me/api-keys          Create new API key
DELETE /users/me/api-keys/{id}     Revoke API key
```

#### GET /users/me

```json
// Response 200
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "John Doe",
  "avatar_url": "https://...",
  "role": "user",
  "default_lang": "en",
  "default_voice_id": "JBFqnCBsd6RMkjVDRZzb",
  "caption_style": "yellow_highlight",
  "music_genre": "auto",
  "subscription": {
    "plan": "creator",
    "status": "active",
    "videos_used": 12,
    "videos_limit": 30,
    "current_period_end": "2026-04-25T00:00:00Z"
  },
  "teams": [
    {"id": "uuid", "name": "My Agency", "role": "owner"}
  ],
  "created_at": "2026-03-01T00:00:00Z"
}
```

#### PATCH /users/me

```json
// Request (partial update)
{
  "display_name": "Jane Doe",
  "default_lang": "hi",
  "caption_style": "news_style",
  "music_genre": "upbeat"
}

// Response 200: updated user object
```

#### GET /users/me/usage

```json
// Response 200
{
  "period_start": "2026-03-01",
  "period_end": "2026-03-31",
  "videos_created": 12,
  "videos_limit": 30,
  "overage_count": 0,
  "total_api_cost_usd": 1.32,
  "daily_breakdown": [
    {"date": "2026-03-24", "videos": 2, "cost_usd": 0.22},
    {"date": "2026-03-25", "videos": 1, "cost_usd": 0.11}
  ]
}
```

---

### Provider Keys (BYOK) — `/users/me/provider-keys`

```
GET    /users/me/provider-keys           List connected providers
PUT    /users/me/provider-keys/{provider} Set/update a provider key
DELETE /users/me/provider-keys/{provider} Remove a provider key
POST   /users/me/provider-keys/{provider}/verify  Verify key works
```

#### PUT /users/me/provider-keys/anthropic

```json
// Request
{
  "api_key": "sk-ant-..."
}

// Response 200
{
  "provider": "anthropic",
  "is_active": true,
  "last_verified_at": "2026-03-25T12:00:00Z",
  "key_prefix": "sk-ant-**"
}
```

---

### Jobs — `/jobs`

```
POST   /jobs                        Create a new video generation job
GET    /jobs                        List user's jobs (paginated)
GET    /jobs/{id}                   Get job details + progress
DELETE /jobs/{id}                   Cancel a queued/running job
POST   /jobs/{id}/retry             Retry a failed job
```

#### POST /jobs

```json
// Request
{
  "topic": "SpaceX successfully lands Starship",
  "context": "Tech news channel, energetic style",
  "language": "en",
  "voice_id": "JBFqnCBsd6RMkjVDRZzb",
  "caption_style": "yellow_highlight",
  "music_genre": "upbeat",
  "channel_id": "uuid",               // Optional: YouTube channel for auto-upload
  "auto_upload": false,
  "upload_privacy": "private",
  "scheduled_at": null                 // Optional: ISO timestamp for scheduled generation
}

// Response 202 Accepted
{
  "id": "uuid",
  "status": "queued",
  "topic": "SpaceX successfully lands Starship",
  "progress_pct": 0,
  "created_at": "2026-03-25T12:00:00Z",
  "estimated_duration_seconds": 180
}
```

#### GET /jobs

```json
// GET /jobs?status=completed&limit=10&cursor=xxx

// Response 200
{
  "items": [
    {
      "id": "uuid",
      "topic": "SpaceX successfully lands Starship",
      "status": "completed",
      "progress_pct": 100,
      "current_stage": null,
      "video": {
        "id": "uuid",
        "thumbnail_url": "https://cdn.shortfactory.io/...",
        "duration_seconds": 72.5
      },
      "cost_usd": 0.11,
      "created_at": "2026-03-25T12:00:00Z",
      "completed_at": "2026-03-25T12:03:22Z"
    }
  ],
  "pagination": {
    "next_cursor": "xxx",
    "has_more": true,
    "total": 47
  }
}
```

#### GET /jobs/{id}

```json
// Response 200
{
  "id": "uuid",
  "topic": "SpaceX successfully lands Starship",
  "status": "running",
  "progress_pct": 45,
  "current_stage": "voiceover",
  "stages": [
    {"name": "research",  "status": "done", "duration_ms": 2100},
    {"name": "draft",     "status": "done", "duration_ms": 3500},
    {"name": "broll",     "status": "done", "duration_ms": 12000},
    {"name": "voiceover", "status": "running", "started_at": "..."},
    {"name": "captions",  "status": "pending"},
    {"name": "music",     "status": "pending"},
    {"name": "assemble",  "status": "pending"},
    {"name": "thumbnail", "status": "pending"},
    {"name": "upload",    "status": "pending"}
  ],
  "draft_data": {
    "script": "...",
    "youtube_title": "...",
    "broll_prompts": ["...", "...", "..."],
    "research": "..."
  },
  "video": null,
  "cost_usd": 0.06,
  "used_byok": false,
  "created_at": "2026-03-25T12:00:00Z"
}
```

---

### Videos — `/videos`

```
GET    /videos                      List user's completed videos
GET    /videos/{id}                 Get video details
GET    /videos/{id}/download        Get presigned download URL
DELETE /videos/{id}                 Delete video and S3 files
POST   /videos/{id}/upload-youtube  Upload to YouTube (manual trigger)
```

#### GET /videos/{id}

```json
// Response 200
{
  "id": "uuid",
  "title": "SpaceX Lands Starship!",
  "description": "...",
  "tags": ["spacex", "starship", "space"],
  "script": "...",
  "language": "en",
  "video_url": "https://cdn.shortfactory.io/...",
  "thumbnail_url": "https://cdn.shortfactory.io/...",
  "duration_seconds": 72.5,
  "file_size_bytes": 15728640,
  "resolution": "1080x1920",
  "youtube": {
    "video_id": "dQw4w9WgXcQ",
    "url": "https://youtu.be/dQw4w9WgXcQ",
    "status": "private",
    "uploaded_at": "2026-03-25T12:05:00Z"
  },
  "job_id": "uuid",
  "created_at": "2026-03-25T12:03:22Z",
  "expires_at": null
}
```

---

### Topics — `/topics`

```
GET    /topics/trending             Get cached trending topics
POST   /topics/refresh              Force refresh (rate-limited)
POST   /topics/quick-create         Create job directly from a trending topic
```

#### GET /topics/trending

```json
// Response 200
{
  "items": [
    {
      "title": "SpaceX Starship Lands Successfully",
      "source": "reddit/r/technology",
      "trending_score": 0.92,
      "summary": "SpaceX achieved...",
      "url": "https://reddit.com/...",
      "metadata": {"score": 45200, "num_comments": 3100}
    }
  ],
  "cached_at": "2026-03-25T11:45:00Z",
  "next_refresh_at": "2026-03-25T12:00:00Z"
}
```

#### POST /topics/quick-create

```json
// Request
{
  "topic_title": "SpaceX Starship Lands Successfully",
  "channel_id": "uuid"
}

// Response 202: same as POST /jobs
```

---

### YouTube Channels — `/channels`

```
GET    /channels                    List connected channels
POST   /channels/connect            Start YouTube OAuth flow
GET    /channels/callback           YouTube OAuth callback
PATCH  /channels/{id}               Update channel settings
DELETE /channels/{id}               Disconnect channel
POST   /channels/{id}/verify        Test channel connection
```

#### POST /channels/connect

```json
// Response 200
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

#### GET /channels (after connection)

```json
// Response 200
{
  "items": [
    {
      "id": "uuid",
      "channel_id": "UC...",
      "channel_title": "My Tech Channel",
      "channel_thumbnail": "https://yt3.ggpht.com/...",
      "default_privacy": "private",
      "auto_upload": false,
      "is_active": true,
      "last_upload_at": "2026-03-24T10:00:00Z",
      "team_id": null
    }
  ]
}
```

---

### Teams — `/teams` (Agency Feature)

```
GET    /teams                       List user's teams
POST   /teams                       Create a new team
GET    /teams/{id}                  Get team details
PATCH  /teams/{id}                  Update team settings
DELETE /teams/{id}                  Delete team (owner only)
GET    /teams/{id}/members          List team members
POST   /teams/{id}/members/invite   Invite a member
PATCH  /teams/{id}/members/{uid}    Update member role
DELETE /teams/{id}/members/{uid}    Remove member
GET    /teams/{id}/jobs             List team's jobs
GET    /teams/{id}/channels         List team's shared channels
GET    /teams/{id}/usage            Team usage analytics
```

#### POST /teams

```json
// Request
{
  "name": "Awesome Agency",
  "brand_color": "#FF5722"
}

// Response 201
{
  "id": "uuid",
  "name": "Awesome Agency",
  "slug": "awesome-agency",
  "owner_id": "uuid",
  "brand_color": "#FF5722",
  "max_members": 10,
  "members_count": 1,
  "channels_count": 0,
  "created_at": "2026-03-25T12:00:00Z"
}
```

#### POST /teams/{id}/members/invite

```json
// Request
{
  "email": "teammate@example.com",
  "role": "member"
}

// Response 201
{
  "invite_id": "uuid",
  "email": "teammate@example.com",
  "role": "member",
  "expires_at": "2026-04-01T12:00:00Z"
}
```

---

### Billing — `/billing`

```
GET    /billing/plans               List available plans
GET    /billing/subscription        Get current subscription
POST   /billing/checkout            Create Stripe Checkout session
POST   /billing/portal              Create Stripe Customer Portal session
GET    /billing/invoices            List invoices
GET    /billing/usage               Current period usage
```

#### GET /billing/plans

```json
// Response 200
{
  "plans": [
    {
      "id": "uuid",
      "name": "free",
      "display_name": "Free",
      "price_cents": 0,
      "videos_per_month": 3,
      "channels_limit": 1,
      "team_seats": 1,
      "features": {"caption_styles": false, "byok": false, "trending_topics": false},
      "overage_cents": 0
    },
    {
      "id": "uuid",
      "name": "creator",
      "display_name": "Creator",
      "price_cents": 1900,
      "videos_per_month": 30,
      "channels_limit": 3,
      "team_seats": 1,
      "features": {"caption_styles": true, "byok": true, "trending_topics": true},
      "overage_cents": 75
    }
  ]
}
```

#### POST /billing/checkout

```json
// Request
{
  "plan": "pro"
}

// Response 200
{
  "checkout_url": "https://checkout.stripe.com/c/pay/..."
}
```

---

### Webhooks — `/webhooks`

```
POST   /webhooks/stripe             Stripe webhook handler
```

This endpoint is unauthenticated but verifies the Stripe webhook signature.

---

### Admin — `/admin` (admin role only)

```
GET    /admin/stats                  Dashboard: users, jobs, revenue
GET    /admin/users                  List all users
PATCH  /admin/users/{id}             Update user (ban, change plan, etc.)
GET    /admin/jobs                   List all jobs (filterable)
GET    /admin/system                 System health (Redis, DB, workers)
```

---

## WebSocket — `/ws`

### Job Progress

```
WS /ws/jobs/{job_id}
```

Server pushes events:
```json
{"type": "stage_started", "stage": "broll", "progress_pct": 20}
{"type": "stage_completed", "stage": "broll", "progress_pct": 30, "duration_ms": 12000}
{"type": "stage_started", "stage": "voiceover", "progress_pct": 30}
{"type": "job_completed", "progress_pct": 100, "video_url": "https://..."}
{"type": "job_failed", "error": "ElevenLabs API rate limited", "stage": "voiceover"}
```

### Global Notifications

```
WS /ws/notifications
```

Server pushes:
```json
{"type": "job_completed", "job_id": "uuid", "topic": "...", "thumbnail_url": "..."}
{"type": "upload_completed", "job_id": "uuid", "youtube_url": "..."}
{"type": "usage_warning", "videos_remaining": 3}
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "INSUFFICIENT_QUOTA",
    "message": "You have used all 30 videos for this billing period. Upgrade your plan or wait until April 1.",
    "details": {
      "videos_used": 30,
      "videos_limit": 30,
      "period_end": "2026-03-31"
    }
  }
}
```

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `INVALID_INPUT` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Missing or invalid auth token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INSUFFICIENT_QUOTA` | 402 | Video limit reached, payment required |
| `RATE_LIMITED` | 429 | Too many requests |
| `JOB_ALREADY_RUNNING` | 409 | Duplicate job for same topic |
| `CHANNEL_NOT_CONNECTED` | 400 | Tried to upload without connected channel |
| `PROVIDER_KEY_INVALID` | 400 | BYOK key verification failed |
| `PLAN_LIMIT_EXCEEDED` | 402 | Feature not available on current plan |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Rate Limits

| Tier | Requests/min | Jobs/hour | WebSocket connections |
|------|-------------|-----------|---------------------|
| Free | 30 | 2 | 1 |
| Creator | 60 | 10 | 3 |
| Pro | 120 | 30 | 10 |
| Agency | 300 | 100 | 50 |
| Enterprise | Custom | Custom | Custom |

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1711368000
```
