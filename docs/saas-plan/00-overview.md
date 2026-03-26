# ShortFactory SaaS Platform — Master Plan

> Transform an open-source YouTube Shorts CLI tool into a multi-tenant SaaS platform
> serving both individual creators and agencies.

## Vision

**ShortFactory** is a web platform where anyone can turn a topic into a published
YouTube Short in minutes — no video editing skills, no API keys, no ffmpeg knowledge.
Agencies can manage multiple channels, team members, and clients from a single dashboard.

## Value Proposition

| Audience | Pain Point | ShortFactory Solution |
|----------|-----------|----------------------|
| Solo creators | Video editing is slow, expensive, repetitive | One-click Shorts from a topic, $0.50-1.00/video |
| Agencies | Managing multiple client channels at scale | Multi-channel dashboard, team seats, white-label |
| News channels | Staying on top of trending topics 24/7 | Auto-discover + auto-produce + scheduled posting |
| Non-technical users | CLI tools, API keys, ffmpeg are intimidating | Zero-setup web UI, everything hosted |

## Business Model

### Pricing Tiers

| Tier | Price | Videos/mo | Channels | Team Seats | Target |
|------|-------|-----------|----------|------------|--------|
| **Free** | $0 | 3 | 1 | 1 | Trial / hobby |
| **Creator** | $19/mo | 30 | 3 | 1 | Solo YouTubers |
| **Pro** | $49/mo | 100 | 10 | 3 | Serious creators |
| **Agency** | $149/mo | 500 | Unlimited | 10 | Agencies, media companies |
| **Enterprise** | Custom | Custom | Unlimited | Unlimited | Large media orgs |

### Per-Video Overage

- Creator: $0.75/video over limit
- Pro: $0.60/video over limit
- Agency: $0.40/video over limit

### Unit Economics

| Item | Cost |
|------|------|
| Claude API (script) | $0.02 |
| Gemini API (3 b-roll + 1 thumbnail) | $0.04 |
| ElevenLabs (voiceover) | $0.05 |
| Compute (ffmpeg + Whisper) | ~$0.03 |
| Storage + CDN | ~$0.01 |
| **Total COGS per video** | **~$0.15** |
| **Lowest selling price** | **$0.40/video** |
| **Gross margin** | **62-85%** |

### BYOK (Bring Your Own Keys) Discount

Users who provide their own API keys get a per-video discount since the platform
doesn't pay the API costs:
- BYOK price: 50% discount on per-video overage
- Platform still charges for compute, storage, and features

## Architecture Overview

```
                         +------------------+
                         |   Next.js SPA    |
                         |   (Frontend)     |
                         +--------+---------+
                                  |
                              HTTPS/WSS
                                  |
                         +--------+---------+
                         |   FastAPI        |
                         |   (API Server)   |
                         +--+-----+-----+--+
                            |     |     |
                   +--------+  +--+--+  +--------+
                   |           |     |           |
              +----+----+ +---+---+ +----+----+
              |PostgreSQL| | Redis | |   S3    |
              |(Database)| |(Queue)| |(Storage)|
              +----------+ +---+---+ +---------+
                               |
                        +------+------+
                        |   Celery    |
                        |  Workers    |
                        +------+------+
                               |
                    +----------+----------+
                    |          |          |
               +----+---+ +---+----+ +---+----+
               |Pipeline | |ffmpeg  | |Whisper |
               |Adapter  | |Encoder | |Model   |
               +----+----+ +--------+ +--------+
                    |
          +---------+---------+
          |         |         |
     +----+---+ +--+---+ +---+----+
     |Claude  | |Gemini| |Eleven  |
     |  API   | | API  | |Labs API|
     +--------+ +------+ +--------+
```

## Plan Documents

| Doc | Content |
|-----|---------|
| [01-codebase-analysis](01-codebase-analysis.md) | Current codebase review, hidden gems, optimization opportunities |
| [02-architecture](02-architecture.md) | Full SaaS architecture with technology choices |
| [02a-monorepo](02a-monorepo.md) | Turborepo + pnpm monorepo structure, polyglot Python/TS setup |
| [03-database-schema](03-database-schema.md) | Complete PostgreSQL schema with all tables |
| [04-api-design](04-api-design.md) | REST API specification — every endpoint |
| [05-pipeline-adapter](05-pipeline-adapter.md) | Refactoring CLI pipeline into a SaaS-callable library |
| [06-auth-and-billing](06-auth-and-billing.md) | Authentication, Stripe integration, subscription management |
| [07-task-queue](07-task-queue.md) | Celery workers, job orchestration, real-time updates |
| [08-frontend](08-frontend.md) | Next.js frontend — pages, components, API integration |
| [08a-visual-design](08a-visual-design.md) | Visual design system — 3D hero, animation stack, color/typography, performance budgets |
| [09-deployment](09-deployment.md) | Docker, CI/CD, infrastructure, monitoring |
| [10-agency-features](10-agency-features.md) | Multi-team, white-label, agency-specific features |
| [11-implementation-roadmap](11-implementation-roadmap.md) | Phased roadmap with milestones and deliverables |
| [12-agent-execution-plan](12-agent-execution-plan.md) | Phase 0 agent team brief — exact files, code patterns, verification steps |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend framework | FastAPI | Async-native, auto OpenAPI docs, fast, perfect for API-first SaaS |
| Task queue | Celery + Redis | Industry standard, battle-tested, supports priority queues |
| Database | PostgreSQL | ACID compliance, JSON support, scales vertically for years |
| ORM | SQLAlchemy 2.0 | Async support, mature, Alembic for migrations |
| Frontend | Next.js 15 (App Router) | SSR, great DX, Vercel deployment, shadcn/ui components |
| 3D / Animation | R3F + GSAP + Framer Motion + Rive | Cinematic landing hero, scroll-driven, performant (see [08a-visual-design](08a-visual-design.md)) |
| Monorepo | Turborepo + pnpm workspaces | Unified builds, shared configs, remote caching for CI |
| Storage | S3-compatible (Cloudflare R2) | Zero egress fees, CDN-friendly, store S3 keys (never presigned URLs) |
| Auth | JWT (httpOnly cookies) + OAuth2 | Secure token storage, social login (Google/GitHub) |
| Real-time updates | SSE for job progress, WebSocket for notifications | SSE is simpler, auto-reconnects, CDN-friendly for unidirectional updates |
| Primary keys | UUIDv7 | Time-ordered (no B-tree fragmentation), standard 128-bit UUID |
| Payments | Stripe | Subscriptions + usage-based billing + webhooks |
| Deployment | Docker + Railway/Fly.io | Simple to start, easy to scale to k8s later |
| API keys model | Hybrid (platform + BYOK) | Lower barrier to entry, power-user flexibility |
| Audience | Creators + Agencies from day 1 | Team features built into core, not bolted on |
