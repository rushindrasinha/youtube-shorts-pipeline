# 09 — Deployment & Infrastructure

## Docker Setup

### API Server Dockerfile

```dockerfile
# docker/Dockerfile.api
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-saas.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-saas.txt

# Copy application code
COPY pipeline/ ./pipeline/
COPY saas/ ./saas/
COPY alembic.ini ./
COPY music/ ./music/

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "saas.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Worker Dockerfile (with ffmpeg + Whisper)

```dockerfile
# docker/Dockerfile.worker
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (ffmpeg, libass for ASS subtitles)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-saas.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-saas.txt

# Pre-download Whisper model during build (cached in image)
RUN python -c "import whisper; whisper.load_model('base')"

# Copy application code
COPY pipeline/ ./pipeline/
COPY saas/ ./saas/
COPY music/ ./music/

# Create non-root user with temp directory access
RUN useradd -m appuser && mkdir -p /tmp/shortfactory && chown -R appuser:appuser /app /tmp/shortfactory
USER appuser

CMD ["celery", "-A", "saas.workers.celery_app", "worker", "-Q", "video,video_priority", "-c", "4", "--loglevel=info"]
```

### Docker Compose — Development

```yaml
# docker/docker-compose.yml
version: "3.9"

services:
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    env_file: ../.env
    depends_on:
      - postgres
      - redis
    volumes:
      - ../pipeline:/app/pipeline    # Hot-reload pipeline code
      - ../saas:/app/saas            # Hot-reload SaaS code
    command: uvicorn saas.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    env_file: ../.env
    depends_on:
      - postgres
      - redis
    volumes:
      - ../pipeline:/app/pipeline
      - ../saas:/app/saas
      - ../music:/app/music

  worker-maintenance:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    env_file: ../.env
    depends_on:
      - postgres
      - redis
    command: celery -A saas.workers.celery_app worker -Q maintenance -c 2 --loglevel=info

  beat:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    env_file: ../.env
    depends_on:
      - redis
    command: celery -A saas.workers.celery_app beat --loglevel=info

  flower:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    ports:
      - "5555:5555"
    env_file: ../.env
    depends_on:
      - redis
    command: celery -A saas.workers.celery_app flower --port=5555

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: shortfactory
      POSTGRES_USER: shortfactory
      POSTGRES_PASSWORD: localdev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    volumes:
      - ../frontend/src:/app/src     # Hot-reload

volumes:
  pgdata:
  redisdata:
```

---

## Environment Variables

```bash
# .env.example

# ─── Database ───
DATABASE_URL=postgresql://shortfactory:localdev@localhost:5432/shortfactory
DATABASE_URL_ASYNC=postgresql+asyncpg://shortfactory:localdev@localhost:5432/shortfactory

# ─── Redis ───
REDIS_URL=redis://localhost:6379/0

# ─── Auth ───
JWT_SECRET_KEY=generate-a-256-bit-random-key-here
ENCRYPTION_KEY=generate-with-fernet-generate-key

# ─── OAuth (Social Login) ───
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx

# ─── Stripe ───
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# ─── Platform API Keys (shared for all users without BYOK) ───
PLATFORM_ANTHROPIC_API_KEY=sk-ant-xxx
PLATFORM_GEMINI_API_KEY=xxx
PLATFORM_ELEVENLABS_API_KEY=xxx

# ─── S3-Compatible Storage ───
S3_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=xxx
S3_SECRET_ACCESS_KEY=xxx
S3_BUCKET_NAME=shortfactory-media
S3_PUBLIC_URL=https://media.shortfactory.io     # CDN URL

# ─── YouTube OAuth (Platform App) ───
YOUTUBE_CLIENT_ID=xxx.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=xxx

# ─── Frontend ───
FRONTEND_URL=http://localhost:3000

# ─── Monitoring ───
SENTRY_DSN=https://xxx@sentry.io/xxx

# ─── App ───
ENVIRONMENT=development      # development, staging, production
LOG_LEVEL=INFO
```

---

## Production Deployment Options

### Option A: Railway (Recommended for Launch)

Railway offers simple container deployment with managed PostgreSQL and Redis:

```
Railway Project:
├── API Service          (docker/Dockerfile.api)
├── Worker Service       (docker/Dockerfile.worker) × 2-4 instances
├── Beat Service         (docker/Dockerfile.worker, beat command)
├── PostgreSQL           (managed)
├── Redis                (managed)
└── Frontend             (Next.js on Vercel, separate)
```

**Estimated cost at launch:**
- API: $5-20/mo (auto-scaled)
- Workers: $10-40/mo each (CPU-intensive, 2-4 instances)
- PostgreSQL: $5-20/mo
- Redis: $5-10/mo
- **Total: ~$30-110/mo** (scales with usage)

### Option B: Fly.io

Similar to Railway but with better geographic distribution:
- API: `fly.toml` with auto-scaling
- Workers: separate app with GPU machines for Whisper
- PostgreSQL: Fly Postgres (managed)
- Redis: Fly Redis (Upstash)

### Option C: AWS (Scale Phase)

When traffic justifies the complexity:
- API: ECS Fargate or EKS
- Workers: ECS with GPU instances (p3.2xlarge for Whisper)
- PostgreSQL: RDS
- Redis: ElastiCache
- Storage: S3 + CloudFront
- Monitoring: CloudWatch + X-Ray

---

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: shortfactory_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt -r requirements-saas.txt
          pip install pytest pytest-mock pytest-asyncio

      - name: Install ffmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg

      - name: Run pipeline tests
        run: python -m pytest tests/pipeline/ -v

      - name: Run SaaS tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/shortfactory_test
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET_KEY: test-secret-key
          ENCRYPTION_KEY: dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItY2k=
        run: python -m pytest tests/saas/ -v

      - name: Lint
        run: |
          pip install ruff
          ruff check pipeline/ saas/

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: api

      - name: Run migrations
        run: |
          # Railway CLI run migration
          railway run alembic upgrade head
```

---

## Storage Service (S3-Compatible)

```python
# saas/services/storage_service.py

import boto3
from botocore.config import Config
from saas.settings import settings


class StorageService:
    """S3-compatible storage for media files (Cloudflare R2, MinIO, AWS S3)."""

    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.S3_BUCKET_NAME
        self.public_url = settings.S3_PUBLIC_URL

    def upload_file(self, local_path: str, s3_key: str, content_type: str = "application/octet-stream") -> dict:
        """Upload a file to S3. Returns dict with s3_key and public_url."""
        self.s3.upload_file(
            local_path,
            self.bucket,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )
        return {
            "s3_key": s3_key,
            "public_url": f"{self.public_url}/{s3_key}",
        }

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned download URL (1 hour default)."""
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )

    def delete_file(self, s3_key: str):
        """Delete a file from S3."""
        self.s3.delete_object(Bucket=self.bucket, Key=s3_key)

    def delete_prefix(self, prefix: str):
        """Delete all files under a prefix (e.g., user_id/job_id/)."""
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                self.s3.delete_object(Bucket=self.bucket, Key=obj["Key"])
```

---

## Monitoring & Observability

### Sentry (Error Tracking)

```python
# saas/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration(), CeleryIntegration()],
    traces_sample_rate=0.1,    # 10% of requests traced
    environment=settings.ENVIRONMENT,
)
```

### Health Check Endpoint

```python
# saas/api/v1/health.py

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    checks = {}

    # Database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Celery workers
    try:
        from saas.workers.celery_app import app as celery_app
        i = celery_app.control.inspect()
        active = i.active()
        checks["workers"] = f"ok ({len(active or {})} workers)"
    except Exception as e:
        checks["workers"] = f"error: {e}"

    all_ok = all(v == "ok" or v.startswith("ok") for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if all_ok else "degraded", "checks": checks},
    )
```

### Key Metrics to Track

| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| Job success rate | Percentage | < 95% over 1h |
| Job avg duration | Histogram | > 300s p95 |
| Active workers | Gauge | < 2 |
| Queue depth | Gauge | > 50 (video), > 10 (priority) |
| API response time | Histogram | > 500ms p95 |
| API error rate | Percentage | > 5% over 5m |
| S3 storage used | Gauge | > 80% of budget |
| Monthly API cost | Counter | > budget threshold |
| Active subscriptions | Gauge | - |
| MRR (Monthly Recurring Revenue) | Gauge | - |
