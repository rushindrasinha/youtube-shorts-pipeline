# 12 — Agent Execution Plan: Phase 0 (Foundation)

> This document is the execution brief for the agent team. Each section is a
> self-contained work unit that can be assigned to one agent. Work units within
> the same step can run in parallel. Work units across steps are sequential.
>
> **Reference docs:** Every instruction links to the planning doc with exact
> specifications. Agents must read the referenced doc section before coding.

---

## Principles (Read This First)

1. **No orphan code.** Every file you create must be imported somewhere, tested,
   or referenced in a config. If nothing uses it, don't create it.
2. **DRY from day one.** If two files share logic, extract it. Don't say "we'll
   refactor later." There is no later.
3. **Backward compatible.** The existing CLI (`python -m pipeline run --news "..."`)
   must work identically after all changes. Every modification to `pipeline/` is
   additive — new optional parameters defaulting to `None`.
4. **Test as you go.** Every service, every model, every endpoint gets a test in
   the same PR. Not a "testing phase" later.
5. **Commit granularity.** One logical change per commit. "Add JobConfig dataclass"
   is a commit. "Modify 8 pipeline modules" is not.

---

## Step 0: Monorepo Scaffold

**Agent count:** 1
**Estimated scope:** ~15 files created, 0 existing files modified
**Reference:** [02a-monorepo.md](02a-monorepo.md)

### Agent A: Monorepo & Tooling

**Context:** We are converting a flat Python repo into a Turborepo + pnpm monorepo.
The existing `pipeline/`, `tests/`, `music/`, `scripts/`, `docs/` directories stay
exactly where they are. New directories are created alongside them.

**Create these files exactly:**

```
turbo.json
package.json              (root)
pnpm-workspace.yaml
.npmrc
apps/
  web/
    package.json
    next.config.ts
    tsconfig.json
    tailwind.config.ts
    postcss.config.js
    src/
      app/
        layout.tsx        (root layout — dark theme, Inter + Space Grotesk fonts)
        page.tsx          (placeholder: "ShortFactory — Coming Soon")
        globals.css       (Tailwind directives + CSS variables from 08a-visual-design.md)
      lib/
        utils.ts          (cn() helper — re-export from @repo/ui)
  api/
    package.json          (Turborepo shim — scripts shell out to Python commands)
packages/
  ui/
    package.json
    tsconfig.json
    src/
      index.ts            (barrel export)
      button.tsx          (shadcn Button — first component)
      card.tsx            (shadcn Card)
  tsconfig/
    package.json
    base.json
    nextjs.json
    react-library.json
  eslint-config/
    package.json
    base.js
    next.js
```

**Root `package.json`:**
```json
{
  "name": "shortfactory",
  "private": true,
  "scripts": {
    "build": "turbo run build",
    "dev": "turbo run dev",
    "dev:web": "turbo run dev --filter=@repo/web",
    "dev:api": "turbo run dev --filter=@repo/api",
    "lint": "turbo run lint",
    "test": "turbo run test",
    "typecheck": "turbo run typecheck",
    "db:migrate": "cd apps/api && alembic upgrade head",
    "format": "prettier --write \"**/*.{ts,tsx,md,json}\""
  },
  "devDependencies": {
    "turbo": "^2.0",
    "prettier": "^3.0"
  },
  "packageManager": "pnpm@9.0.0"
}
```

**`turbo.json`:**
```json
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": [".env"],
  "tasks": {
    "build": { "dependsOn": ["^build"], "outputs": [".next/**", "dist/**"] },
    "dev": { "cache": false, "persistent": true },
    "lint": { "dependsOn": ["^build"] },
    "typecheck": { "dependsOn": ["^build"] },
    "test": { "dependsOn": ["^build"], "outputs": ["coverage/**"] },
    "clean": { "cache": false }
  }
}
```

**`pnpm-workspace.yaml`:**
```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

**`apps/web/src/app/globals.css`** — must contain the CSS variables from
[08a-visual-design.md](08a-visual-design.md) "Color System" section. Use `@theme`
for Tailwind v4, or `@layer base` + `:root` for v3.

**`apps/web/src/app/layout.tsx`** — must use `next/font` to load Inter (body) and
Space Grotesk (display). Set `<html className="dark">`. Apply `bg-[#09090b]` and
`text-zinc-50` to body.

**Verification:**
```bash
pnpm install
pnpm build           # Should succeed (web builds, api echoes)
pnpm dev:web         # Should start Next.js on port 3000
```

**Do NOT:**
- Move any existing files
- Modify any existing Python files
- Install Python dependencies (that's another agent's job)

---

## Step 1: Pipeline Adapter + Database + Docker (parallel)

**Agent count:** 3 (run in parallel)
**Reference:** [05-pipeline-adapter.md](05-pipeline-adapter.md), [03-database-schema.md](03-database-schema.md), [09-deployment.md](09-deployment.md)

### Agent B: Pipeline Adapter Layer

**Context:** The existing pipeline is a CLI tool where every module reads from a global
config file. For SaaS, each job needs its own config (different API keys, voices,
languages). You're adding an adapter layer that wraps the CLI functions with injected
configuration.

**Read first:** [05-pipeline-adapter.md](05-pipeline-adapter.md) — entire file.
Study the `JobConfig` dataclass, the proposed changes to each module, and the
`PipelineJob` class.

**Files to modify (all changes are additive — add optional params, never remove existing ones):**

1. **`pipeline/config.py`** — Add `JobConfig` dataclass (ref: 05-pipeline-adapter.md §1):
   ```python
   @dataclass
   class JobConfig:
       job_id: str
       work_dir: Path
       topic: str = ""
       context: str = ""
       anthropic_api_key: str = ""
       gemini_api_key: str = ""
       elevenlabs_api_key: str = ""
       voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
       language: str = "en"
       caption_style: str = "yellow_highlight"
       music_genre: str = "auto"
       video_width: int = 1080
       video_height: int = 1920
       youtube_access_token: str = ""
       youtube_refresh_token: str = ""
       on_progress: callable = None
       on_log: callable = None
   ```
   - Modify `_get_key()` to accept an optional `override: str = ""` parameter
   - Add `get_anthropic_key(override="")`, same pattern for gemini, elevenlabs

2. **`pipeline/state.py`** — Add `start_stage()` and progress callback (ref: 05-pipeline-adapter.md §2):
   - Constructor gains `on_progress: callable = None`
   - `start_stage(stage)` marks running + fires callback
   - `complete_stage()` fires callback with percentage
   - `_calculate_progress()` computes % from stage index

3. **`pipeline/draft.py`** — Add `config: JobConfig = None` to `generate_draft()` (ref: 05-pipeline-adapter.md §4):
   - When `config` provided and has `anthropic_api_key`, use it directly
   - Otherwise fall through to existing `_call_claude()` logic

4. **`pipeline/broll.py`** — Add config injection + parallel generation (ref: 05-pipeline-adapter.md §3):
   - `generate_broll()` gains `config: JobConfig = None`
   - When config present, use `config.gemini_api_key`
   - Replace sequential loop with `ThreadPoolExecutor(max_workers=3)`
   - Existing fallback behavior preserved

5. **`pipeline/voiceover.py`** — Add `config: JobConfig = None` (ref: 05-pipeline-adapter.md §5):
   - Use `config.voice_id` and `config.elevenlabs_api_key` when present

6. **`pipeline/captions.py`** — Cache Whisper model at module level (ref: 05-pipeline-adapter.md §6):
   - Add `_whisper_model = None` and `_get_whisper_model()` function
   - `_whisper_word_timestamps()` uses cached model
   - This is the ONLY place Whisper loads — no worker_init loading elsewhere

7. **`pipeline/upload.py`** — Add `config: JobConfig = None` (ref: 05-pipeline-adapter.md §7):
   - When config has `youtube_access_token`, build credentials from it
   - Otherwise use existing file-based OAuth flow

8. **`pipeline/music.py`** — Add `config: JobConfig = None`:
   - Use `config.music_genre` when present (for future genre selection)

9. **`pipeline/adapter.py`** — CREATE new file with `PipelineJob` class (ref: 05-pipeline-adapter.md bottom):
   - `__init__(config: JobConfig)` sets up job
   - `run()` executes all stages sequentially, returns result dict
   - `upload()` optionally uploads to YouTube
   - `_emit_progress()` helper calls `config.on_progress`
   - Progress callback is thread-safe (see thread safety note in 05-pipeline-adapter.md)

10. **`pipeline/__init__.py`** — Export `PipelineJob` and `JobConfig`:
    ```python
    from .adapter import PipelineJob
    from .config import JobConfig
    ```

**Replace `openai-whisper` with `faster-whisper`:**
- In `requirements.txt`: replace `openai-whisper>=20231117` with `faster-whisper>=1.0.0`
- In `pipeline/captions.py`: change import from `import whisper` to `from faster_whisper import WhisperModel`
- Adapt `_get_whisper_model()` and `_whisper_word_timestamps()` for faster-whisper API:
  ```python
  def _get_whisper_model():
      global _whisper_model
      if _whisper_model is None:
          from faster_whisper import WhisperModel
          _whisper_model = WhisperModel("base", compute_type="int8")
      return _whisper_model
  ```
- The word-level timestamps API differs slightly — adapt the parsing logic

**Tests to write (in `tests/`):**

- `tests/test_adapter.py`:
  - `test_pipeline_job_runs_all_stages` — mock every API call, verify all stages complete
  - `test_pipeline_job_emits_progress` — verify on_progress called for each stage
  - `test_pipeline_job_handles_failure` — simulate stage failure, verify error in result
  - `test_job_config_defaults` — verify sensible defaults
- `tests/test_broll_parallel.py`:
  - `test_broll_generates_3_frames_concurrently` — mock Gemini, verify ThreadPoolExecutor used

**Verification:**
```bash
python -m pytest tests/ -v                   # All tests pass (old + new)
python -m pipeline run --news "test" --dry-run  # CLI still works
python -c "from pipeline import PipelineJob, JobConfig; print('OK')"  # Import works
```

**Do NOT:**
- Touch `pipeline/__main__.py` (CLI stays untouched)
- Add any SaaS/web dependencies to `requirements.txt`
- Create any files outside `pipeline/` and `tests/`

---

### Agent C: Database Models + Alembic

**Context:** You're creating the PostgreSQL schema for the SaaS platform using
SQLAlchemy 2.0. All tables use UUIDv7 primary keys. The schema lives under
`apps/api/saas/models/`.

**Read first:** [03-database-schema.md](03-database-schema.md) — entire file.
Note the UUIDv7 requirement, ON DELETE policies, composite indexes, key_version
columns, and the JSONB usage notes.

**Create `apps/api/` directory structure:**

```
apps/api/
  saas/
    __init__.py
    settings.py                    # Pydantic Settings — all env vars
    models/
      __init__.py                  # Import all models, create Base
      base.py                      # SQLAlchemy DeclarativeBase + UUIDv7 mixin
      user.py                      # User, OAuthConnection, UserAPIKey
      team.py                      # Team, TeamMember, TeamInvite
      job.py                       # Job, JobStage
      video.py                     # Video
      channel.py                   # YouTubeChannel
      subscription.py              # Plan, Subscription, UsageRecord
      api_keys.py                  # UserProviderKey
      audit.py                     # AuditLog
      topic_cache.py               # TrendingTopicCache
  alembic.ini
  migrations/
    env.py
    versions/
      .gitkeep
  requirements-saas.txt
  .env.example
```

**`saas/models/base.py`** — Reusable base and mixins:
```python
from datetime import datetime, timezone
from uuid import UUID
import uuid7
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class UUIDMixin:
    """All tables use UUIDv7 (time-ordered, no B-tree fragmentation)."""
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=lambda: uuid7.uuid7(),
    )

class TimestampMixin:
    """created_at + updated_at on all tables."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

**Every model class** must inherit from `Base, UUIDMixin, TimestampMixin`.

**`saas/settings.py`** — Single source for all config (ref: [09-deployment.md](09-deployment.md) "Environment Variables"):
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://shortfactory:localdev@localhost:5432/shortfactory"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "change-me-in-production"
    ENCRYPTION_KEY: str = "change-me-in-production"
    # ... all env vars from .env.example

    class Config:
        env_file = ".env"

settings = Settings()
```

**`requirements-saas.txt`** (ref: [06-auth-and-billing.md](06-auth-and-billing.md) "Dependencies to Add"):
```
fastapi>=0.115.0,<1.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.0,<3.0
alembic>=1.13.0,<2.0
asyncpg>=0.29.0
psycopg2-binary>=2.9.0
redis>=5.0.0,<6.0
celery[redis]>=5.3.0,<6.0
stripe>=8.0.0,<9.0
pyjwt>=2.8.0,<3.0
bcrypt>=4.1.0,<5.0
cryptography>=42.0.0,<43.0
authlib>=1.3.0,<2.0
httpx>=0.27.0,<1.0
python-multipart>=0.0.7
pydantic-settings>=2.0.0,<3.0
sentry-sdk[fastapi]>=1.40.0
uuid7>=0.1.0
```

**Model implementation rules:**
- Use `Mapped[...]` type annotations (SQLAlchemy 2.0 style, not `Column()`)
- Use `relationship()` with `back_populates` (not `backref` — it's deprecated)
- Every FK must have an explicit `ondelete` parameter matching 03-database-schema.md
- JSONB columns use `mapped_column(type_=JSON)` with Python `dict` type hint
- Add `__tablename__` on every model
- The `plans` table must have a seed script in `migrations/versions/` that inserts
  the 5 plans from 03-database-schema.md

**Alembic setup:**
- `alembic.ini` with `sqlalchemy.url` from settings
- `migrations/env.py` must import all models from `saas.models` so autogenerate finds them
- Create initial migration: `alembic revision --autogenerate -m "initial schema"`

**Tests to write:**
- `tests/saas/test_models.py`:
  - `test_user_creation` — create user, verify UUIDv7 PK, timestamps
  - `test_job_stages_cascade` — delete job → stages cascade
  - `test_team_owner_restrict` — deleting user who owns team raises IntegrityError
  - `test_plan_seed_data` — verify 5 plans exist after migration

**Verification:**
```bash
cd apps/api
pip install -r requirements-saas.txt
alembic upgrade head                           # Migration runs
python -c "from saas.models import *; print('Models loaded')"
python -m pytest tests/saas/test_models.py -v  # Model tests pass
```

**Do NOT:**
- Create API endpoints (that's Phase 1)
- Create services (that's Phase 1)
- Add any frontend code

---

### Agent D: Docker + Dev Infrastructure

**Context:** You're creating the Docker setup for local development. Three services:
PostgreSQL, Redis, and a docker-compose file that ties them together. Also Dockerfiles
for the API and worker (used later in production).

**Read first:** [09-deployment.md](09-deployment.md) — Docker section.

**Create these files:**

```
docker/
  Dockerfile.api
  Dockerfile.worker
  docker-compose.yml
.env.example
.gitignore                  (update — add node_modules, .next, .turbo, .env)
```

**`docker/docker-compose.yml`:**
```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: shortfactory
      POSTGRES_USER: shortfactory
      POSTGRES_PASSWORD: localdev
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shortfactory"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redisdata:/data]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
  redisdata:
```

Keep docker-compose minimal for now — only infra services. API and workers run
natively during development (via `pnpm dev:api`).

**`Dockerfile.api`** (production, ref: 09-deployment.md):
- `python:3.12-slim` base
- Install system deps (build-essential)
- Copy and install `requirements.txt` + `requirements-saas.txt`
- Copy `pipeline/` and `apps/api/saas/`
- Create non-root user
- CMD: `uvicorn saas.main:app --host 0.0.0.0 --port 8000 --workers 4`

**`Dockerfile.worker`** (production, ref: 09-deployment.md):
- Same base but add `ffmpeg` and `libass-dev`
- Pre-download faster-whisper model during build
- Copy `pipeline/`, `apps/api/saas/`, `music/`
- CMD: `celery -A saas.workers.celery_app worker -Q video,video_priority -c 2`

**`.env.example`** (ref: 09-deployment.md "Environment Variables"):
- Every variable with a placeholder value and comment
- Group by category: Database, Redis, Auth, OAuth, Stripe, Platform Keys, S3, YouTube, Frontend, Monitoring, App

**Update `.gitignore`** — add:
```
node_modules/
.next/
.turbo/
dist/
.env
.env.local
*.pyc
__pycache__/
.pytest_cache/
coverage/
apps/api/migrations/versions/*.py
!apps/api/migrations/versions/.gitkeep
```

**Verification:**
```bash
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml ps     # postgres + redis healthy
psql postgresql://shortfactory:localdev@localhost:5432/shortfactory -c "SELECT 1"
redis-cli ping                                      # PONG
docker compose -f docker/docker-compose.yml down
```

**Do NOT:**
- Create CI/CD pipeline (that's Phase 4)
- Configure production deployment
- Install pnpm or run npm commands (Agent A handles that)

---

## Step 2: Integration Verification

**Agent count:** 1
**This runs AFTER Step 0 + Step 1 are all complete.**

### Agent E: Integration Test

**Context:** Agents A-D have created the monorepo scaffold, pipeline adapter,
database models, and Docker infra. You need to verify everything works together.

**Tasks:**

1. **Install everything:**
   ```bash
   pnpm install                                    # JS deps
   pip install -r requirements.txt                 # Pipeline deps
   pip install -r apps/api/requirements-saas.txt   # SaaS deps
   ```

2. **Start infrastructure:**
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

3. **Run database migration:**
   ```bash
   cd apps/api && alembic upgrade head
   ```

4. **Run ALL tests:**
   ```bash
   python -m pytest tests/ -v                      # Pipeline tests (existing + new)
   python -m pytest tests/saas/ -v                 # SaaS model tests
   pnpm build                                      # Turborepo builds everything
   pnpm typecheck                                  # TypeScript type checking
   ```

5. **Verify CLI backward compatibility:**
   ```bash
   python -m pipeline run --news "test topic" --dry-run
   ```

6. **Verify adapter works:**
   ```python
   from pipeline import PipelineJob, JobConfig
   from pathlib import Path
   import tempfile

   config = JobConfig(
       job_id="test-123",
       work_dir=Path(tempfile.mkdtemp()),
       topic="Test topic",
   )
   job = PipelineJob(config)
   # Don't actually run (needs API keys), just verify construction
   print(f"Job {job.job_id} ready, work_dir={job.work_dir}")
   ```

7. **Verify web dev server:**
   ```bash
   pnpm dev:web   # Should start Next.js on :3000
   # Visit http://localhost:3000 — should see "ShortFactory — Coming Soon"
   ```

8. **Fix any issues found** — this is the integration safety net.

**Deliverable:** A single commit with any fixes needed. After this, the foundation
is solid and Phase 1 can begin.

---

## Dependency Graph

```
Step 0: Agent A (Monorepo)
            │
            ▼
Step 1: ┌── Agent B (Pipeline Adapter) ─┐
        │   Agent C (Database Models)    ├── all parallel
        │   Agent D (Docker Infra)      ─┘
            │
            ▼
Step 2: Agent E (Integration Test)
```

---

## Agent Checklist (Copy-Paste for Each Agent)

Before marking your work complete, verify:

- [ ] Every new file has a clear purpose (no empty placeholder files)
- [ ] Every import works (`python -c "from X import Y"`)
- [ ] Every new function has at least one test
- [ ] No hardcoded secrets, paths, or URLs (use settings/env vars)
- [ ] No `# TODO` or `# FIXME` left behind (do it now or don't create the file)
- [ ] `python -m pytest tests/ -v` passes
- [ ] If you created TypeScript: `pnpm typecheck` passes
- [ ] If you modified `pipeline/`: `python -m pipeline run --news "test" --dry-run` still works
- [ ] Commit messages are descriptive (what + why, not "update files")
