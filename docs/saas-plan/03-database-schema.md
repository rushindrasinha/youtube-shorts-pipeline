# 03 — Database Schema (PostgreSQL)

## Overview

All tables use UUIDs as primary keys, UTC timestamps, and soft-delete where
appropriate. The schema supports both individual creators and agency teams
from day one.

---

## ER Diagram (Simplified)

```
User ──1:N──→ TeamMember ──N:1──→ Team
User ──1:N──→ YouTubeChannel
User ──1:N──→ Job ──1:1──→ Video
User ──1:N──→ UserProviderKey
User ──1:1──→ Subscription ──N:1──→ Plan
User ──1:N──→ UsageRecord
User ──1:N──→ UserAPIKey
Team ──1:N──→ YouTubeChannel (shared channels)
Team ──1:N──→ Job (team-scoped jobs)
Job  ──1:N──→ JobStage
```

---

## Table Definitions

### users

Primary user table. Supports email/password and OAuth login.

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    email_verified  BOOLEAN DEFAULT FALSE,
    password_hash   VARCHAR(255),                    -- NULL for OAuth-only users
    display_name    VARCHAR(100),
    avatar_url      VARCHAR(500),
    role            VARCHAR(20) DEFAULT 'user',      -- user, admin
    is_active       BOOLEAN DEFAULT TRUE,
    stripe_customer_id VARCHAR(255) UNIQUE,

    -- Preferences (persisted per user)
    default_lang    VARCHAR(5) DEFAULT 'en',
    default_voice_id VARCHAR(100),
    caption_style   VARCHAR(50) DEFAULT 'yellow_highlight',
    music_genre     VARCHAR(50) DEFAULT 'auto',

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_stripe ON users(stripe_customer_id);
```

### oauth_connections

Stores OAuth provider connections (Google, GitHub) for social login.

```sql
CREATE TABLE oauth_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider        VARCHAR(50) NOT NULL,            -- google, github
    provider_user_id VARCHAR(255) NOT NULL,
    access_token_enc TEXT,                           -- Fernet encrypted
    refresh_token_enc TEXT,                          -- Fernet encrypted
    token_expires_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(provider, provider_user_id)
);

CREATE INDEX idx_oauth_user ON oauth_connections(user_id);
```

### user_api_keys

API keys for programmatic access to the ShortFactory API.

```sql
CREATE TABLE user_api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    key_prefix      VARCHAR(8) NOT NULL,             -- First 8 chars shown in UI
    key_hash        VARCHAR(255) NOT NULL,            -- bcrypt hash of full key
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user ON user_api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON user_api_keys(key_prefix);
```

### user_provider_keys

BYOK: User-provided API keys for Anthropic, Gemini, ElevenLabs.

```sql
CREATE TABLE user_provider_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider        VARCHAR(50) NOT NULL,            -- anthropic, gemini, elevenlabs
    api_key_enc     TEXT NOT NULL,                    -- Fernet encrypted
    is_active       BOOLEAN DEFAULT TRUE,
    last_verified_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, provider)
);

CREATE INDEX idx_provider_keys_user ON user_provider_keys(user_id);
```

### teams

Agency/team support. A user can own multiple teams.

```sql
CREATE TABLE teams (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,     -- URL-friendly name
    owner_id        UUID NOT NULL REFERENCES users(id),
    logo_url        VARCHAR(500),

    -- White-label settings
    brand_color     VARCHAR(7),                       -- #hex color
    custom_domain   VARCHAR(255),                     -- e.g. shorts.agency.com

    max_members     INTEGER DEFAULT 10,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_teams_owner ON teams(owner_id);
CREATE INDEX idx_teams_slug ON teams(slug);
```

### team_members

```sql
CREATE TABLE team_members (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) DEFAULT 'member',     -- owner, admin, member, viewer
    invited_by      UUID REFERENCES users(id),
    joined_at       TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(team_id, user_id)
);

CREATE INDEX idx_team_members_team ON team_members(team_id);
CREATE INDEX idx_team_members_user ON team_members(user_id);
```

### team_invites

```sql
CREATE TABLE team_invites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    role            VARCHAR(20) DEFAULT 'member',
    invited_by      UUID NOT NULL REFERENCES users(id),
    token           VARCHAR(255) UNIQUE NOT NULL,     -- Unique invite token
    accepted_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invites_token ON team_invites(token);
CREATE INDEX idx_invites_email ON team_invites(email);
```

### youtube_channels

Connected YouTube channels with encrypted OAuth tokens.

```sql
CREATE TABLE youtube_channels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id         UUID REFERENCES teams(id) ON DELETE SET NULL,  -- NULL = personal channel

    channel_id      VARCHAR(100) NOT NULL,            -- YouTube channel ID
    channel_title   VARCHAR(255),
    channel_thumbnail VARCHAR(500),

    -- Encrypted OAuth credentials
    access_token_enc  TEXT NOT NULL,                   -- Fernet encrypted
    refresh_token_enc TEXT,                            -- Fernet encrypted
    token_expires_at  TIMESTAMPTZ,
    scopes           TEXT[],                           -- OAuth scopes granted

    default_privacy  VARCHAR(20) DEFAULT 'private',   -- private, unlisted, public
    auto_upload      BOOLEAN DEFAULT FALSE,
    is_active        BOOLEAN DEFAULT TRUE,
    last_upload_at   TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_channels_user ON youtube_channels(user_id);
CREATE INDEX idx_channels_team ON youtube_channels(team_id);
```

### plans

Subscription plan definitions.

```sql
CREATE TABLE plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(50) UNIQUE NOT NULL,      -- free, creator, pro, agency, enterprise
    display_name    VARCHAR(100) NOT NULL,
    stripe_price_id VARCHAR(255),                     -- Stripe Price ID

    -- Limits
    videos_per_month    INTEGER NOT NULL,
    channels_limit      INTEGER NOT NULL,
    team_seats          INTEGER NOT NULL DEFAULT 1,

    -- Features (JSON for flexibility)
    features        JSONB DEFAULT '{}',               -- {"caption_styles": true, "byok": true, ...}

    -- Pricing
    price_cents     INTEGER NOT NULL,                  -- Monthly price in cents
    overage_cents   INTEGER DEFAULT 0,                 -- Per-video overage cost in cents

    is_active       BOOLEAN DEFAULT TRUE,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Seed plans
INSERT INTO plans (name, display_name, videos_per_month, channels_limit, team_seats, price_cents, overage_cents, features) VALUES
('free',       'Free',       3,   1,  1,   0,     0,  '{"caption_styles": false, "byok": false, "trending_topics": false}'),
('creator',    'Creator',    30,  3,  1,   1900,  75, '{"caption_styles": true, "byok": true, "trending_topics": true}'),
('pro',        'Pro',        100, 10, 3,   4900,  60, '{"caption_styles": true, "byok": true, "trending_topics": true, "priority_queue": true}'),
('agency',     'Agency',     500, -1, 10,  14900, 40, '{"caption_styles": true, "byok": true, "trending_topics": true, "priority_queue": true, "white_label": true, "api_access": true}'),
('enterprise', 'Enterprise', -1,  -1, -1,  0,     0,  '{"all": true}');
-- -1 means unlimited
```

### subscriptions

```sql
CREATE TABLE subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id             UUID NOT NULL REFERENCES plans(id),
    stripe_subscription_id VARCHAR(255) UNIQUE,

    status              VARCHAR(30) DEFAULT 'active',  -- active, past_due, canceled, trialing
    current_period_start TIMESTAMPTZ,
    current_period_end   TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subs_user ON subscriptions(user_id);
CREATE INDEX idx_subs_stripe ON subscriptions(stripe_subscription_id);
```

### jobs

Core table: each video generation request is a "job."

```sql
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id         UUID REFERENCES teams(id) ON DELETE SET NULL,
    channel_id      UUID REFERENCES youtube_channels(id) ON DELETE SET NULL,

    -- Input
    topic           TEXT NOT NULL,
    context         TEXT DEFAULT '',                    -- Channel context / style guidance
    language        VARCHAR(5) DEFAULT 'en',
    voice_id        VARCHAR(100),
    caption_style   VARCHAR(50) DEFAULT 'yellow_highlight',
    music_genre     VARCHAR(50) DEFAULT 'auto',
    auto_upload     BOOLEAN DEFAULT FALSE,
    upload_privacy  VARCHAR(20) DEFAULT 'private',

    -- State
    status          VARCHAR(30) DEFAULT 'queued',      -- queued, running, completed, failed, canceled
    current_stage   VARCHAR(30),                       -- Current pipeline stage
    progress_pct    INTEGER DEFAULT 0,                 -- 0-100
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,

    -- Results (populated on completion)
    video_id        UUID REFERENCES videos(id),

    -- Cost tracking
    cost_usd        DECIMAL(10,4) DEFAULT 0,           -- Actual API cost for this job
    used_byok       BOOLEAN DEFAULT FALSE,             -- Whether user's own keys were used

    -- Pipeline state (preserves the PipelineState from CLI)
    pipeline_state  JSONB DEFAULT '{}',

    -- Draft data (the full Claude-generated draft)
    draft_data      JSONB DEFAULT '{}',

    -- Celery task tracking
    celery_task_id  VARCHAR(255),

    -- Scheduling
    scheduled_at    TIMESTAMPTZ,                        -- NULL = immediate, future = scheduled
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_user ON jobs(user_id);
CREATE INDEX idx_jobs_team ON jobs(team_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created ON jobs(created_at DESC);
CREATE INDEX idx_jobs_scheduled ON jobs(scheduled_at) WHERE scheduled_at IS NOT NULL AND status = 'queued';
```

### job_stages

Detailed per-stage tracking for each job (mirrors PipelineState).

```sql
CREATE TABLE job_stages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    stage_name      VARCHAR(30) NOT NULL,              -- research, draft, broll, voiceover, etc.

    status          VARCHAR(20) DEFAULT 'pending',     -- pending, running, done, failed, skipped
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_ms     INTEGER,                           -- How long this stage took
    error_message   TEXT,

    -- Artifacts (S3 paths, metadata)
    artifacts       JSONB DEFAULT '{}',

    -- Cost for this specific stage
    cost_usd        DECIMAL(10,4) DEFAULT 0,

    UNIQUE(job_id, stage_name)
);

CREATE INDEX idx_stages_job ON job_stages(job_id);
```

### videos

Completed video records with S3 paths and YouTube metadata.

```sql
CREATE TABLE videos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID UNIQUE NOT NULL REFERENCES jobs(id),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id         UUID REFERENCES teams(id),
    channel_id      UUID REFERENCES youtube_channels(id),

    -- Content
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    tags            TEXT[],
    script          TEXT,
    language        VARCHAR(5) DEFAULT 'en',

    -- Storage
    video_url       VARCHAR(500) NOT NULL,             -- S3 presigned or CDN URL
    video_s3_key    VARCHAR(500) NOT NULL,             -- S3 object key
    thumbnail_url   VARCHAR(500),
    thumbnail_s3_key VARCHAR(500),
    srt_s3_key      VARCHAR(500),

    -- Metadata
    duration_seconds DECIMAL(6,2),
    file_size_bytes  BIGINT,
    resolution       VARCHAR(20) DEFAULT '1080x1920',

    -- YouTube (populated after upload)
    youtube_video_id VARCHAR(50),
    youtube_url      VARCHAR(200),
    youtube_status   VARCHAR(30),                       -- private, unlisted, public
    uploaded_to_youtube_at TIMESTAMPTZ,

    -- Expiry (free tier videos expire after 7 days)
    expires_at      TIMESTAMPTZ,

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_videos_user ON videos(user_id);
CREATE INDEX idx_videos_team ON videos(team_id);
CREATE INDEX idx_videos_expires ON videos(expires_at) WHERE expires_at IS NOT NULL;
```

### usage_records

Tracks per-period usage for billing and limit enforcement.

```sql
CREATE TABLE usage_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    period_start    DATE NOT NULL,                     -- First day of billing period
    period_end      DATE NOT NULL,                     -- Last day of billing period

    videos_created  INTEGER DEFAULT 0,
    videos_limit    INTEGER NOT NULL,                  -- Snapshot of plan limit for this period
    overage_count   INTEGER DEFAULT 0,                 -- Videos over the limit

    -- Cost tracking
    total_api_cost  DECIMAL(10,4) DEFAULT 0,
    total_billed    DECIMAL(10,4) DEFAULT 0,

    stripe_usage_record_id VARCHAR(255),               -- Stripe metered billing ID

    UNIQUE(user_id, period_start)
);

CREATE INDEX idx_usage_user_period ON usage_records(user_id, period_start DESC);
```

### trending_topics_cache

Global cache for trending topics (refreshed every 15 min).

```sql
CREATE TABLE trending_topics_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          VARCHAR(50) NOT NULL,              -- reddit, rss, google_trends, etc.
    title           TEXT NOT NULL,
    summary         TEXT,
    url             VARCHAR(500),
    trending_score  DECIMAL(5,3) DEFAULT 0,
    metadata        JSONB DEFAULT '{}',

    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL               -- Typically 15 min after fetch
);

CREATE INDEX idx_topics_expires ON trending_topics_cache(expires_at);
CREATE INDEX idx_topics_score ON trending_topics_cache(trending_score DESC);
```

### audit_log

Audit trail for security-sensitive operations.

```sql
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    team_id         UUID REFERENCES teams(id),

    action          VARCHAR(100) NOT NULL,             -- job.create, channel.connect, key.update, etc.
    resource_type   VARCHAR(50),                       -- job, channel, team, user
    resource_id     UUID,

    details         JSONB DEFAULT '{}',
    ip_address      INET,
    user_agent      TEXT,

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_team ON audit_log(team_id, created_at DESC);
```

---

## Migration Strategy

Use Alembic for all schema changes:

```bash
# Initialize
alembic init saas/migrations

# Create initial migration
alembic revision --autogenerate -m "initial schema"

# Apply
alembic upgrade head

# New migration
alembic revision --autogenerate -m "add_new_table"
```

All migrations are stored in `saas/migrations/versions/` and version-controlled.
