# 02a — Turborepo Monorepo Architecture

## Why Monorepo

With three deployable units (Python pipeline/API, Celery workers, Next.js frontend)
and shared configuration, a monorepo gives us:

- **Unified CI/CD** — one repo, one PR, atomic changes across frontend + backend
- **Shared configs** — TypeScript, ESLint, Tailwind configs shared across packages
- **Remote caching** — Turborepo caches build outputs, skipping unchanged packages in CI
- **Single source of truth** — API types generated once, consumed everywhere

## Why Turborepo + pnpm

Turborepo is the best choice here because:

- **Task orchestration**: Define `build`, `dev`, `lint`, `test`, `typecheck` tasks
  with dependency graphs — Turborepo runs them in optimal parallel order
- **Remote caching**: CI builds are 2-5x faster by reusing cached outputs from
  previous runs (free tier on Vercel, or self-hosted)
- **pnpm workspaces**: Faster installs, strict dependency isolation, disk-efficient
  via content-addressable store

**Handling Python**: Turborepo is JS/TS-native. The Python packages (`pipeline/`,
`saas/`) live in the monorepo but are managed by their own tooling (`uv` or `pip`).
Turborepo orchestrates their tasks (test, lint, migrate) via `package.json` scripts
that shell out to Python commands. This is the standard pattern for polyglot monorepos.

---

## Directory Structure

```
youtube-shorts-pipeline/              # Repository root
├── turbo.json                        # Turborepo task configuration
├── package.json                      # Root: pnpm workspace config + shared scripts
├── pnpm-workspace.yaml               # Workspace package declarations
├── .npmrc                            # pnpm settings (e.g., shamefully-hoist=false)
│
├── apps/
│   ├── web/                          # Next.js frontend (deployable)
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── tsconfig.json             # Extends @repo/tsconfig
│   │   ├── src/
│   │   │   ├── app/                  # Next.js App Router pages
│   │   │   ├── components/           # UI components
│   │   │   ├── lib/                  # API client, auth, utils
│   │   │   └── hooks/                # React hooks
│   │   └── public/
│   │       ├── models/               # 3D .glb models (Draco compressed)
│   │       └── rive/                 # .riv animation files
│   │
│   └── api/                          # Python FastAPI backend (deployable)
│       ├── package.json              # Turborepo task shims (scripts → Python)
│       ├── pyproject.toml            # Python package config
│       ├── saas/                     # FastAPI application
│       │   ├── main.py
│       │   ├── api/
│       │   ├── models/
│       │   ├── services/
│       │   ├── tasks/
│       │   └── workers/
│       ├── alembic.ini
│       └── migrations/
│
├── packages/
│   ├── ui/                           # Shared UI component library
│   │   ├── package.json
│   │   ├── src/
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   └── index.ts              # Barrel export
│   │   └── tsconfig.json
│   │
│   ├── tsconfig/                     # Shared TypeScript configs
│   │   ├── package.json
│   │   ├── base.json
│   │   ├── nextjs.json
│   │   └── react-library.json
│   │
│   └── eslint-config/                # Shared ESLint configs
│       ├── package.json
│       ├── base.js
│       └── next.js
│
├── pipeline/                         # EXISTING Python pipeline (stays in place)
│   ├── __init__.py
│   ├── __main__.py
│   ├── adapter.py                    # SaaS adapter
│   ├── config.py
│   ├── state.py
│   └── ...
│
├── docker/                           # Docker configs
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── docker-compose.yml
│
├── docs/
│   └── saas-plan/                    # These planning documents
│
├── tests/                            # Python tests (pipeline + saas)
├── music/                            # Bundled music tracks
├── pyproject.toml                    # Root Python config (shared deps)
├── requirements.txt                  # Python deps
└── requirements-saas.txt             # SaaS Python deps
```

---

## Configuration Files

### `pnpm-workspace.yaml`

```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

### Root `package.json`

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
    "db:make-migration": "cd apps/api && alembic revision --autogenerate -m",
    "format": "prettier --write \"**/*.{ts,tsx,md,json}\"",
    "clean": "turbo run clean"
  },
  "devDependencies": {
    "turbo": "^2.0",
    "prettier": "^3.0"
  },
  "packageManager": "pnpm@9.0.0"
}
```

### `turbo.json`

```json
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": [".env"],
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {
      "dependsOn": ["^build"]
    },
    "typecheck": {
      "dependsOn": ["^build"]
    },
    "test": {
      "dependsOn": ["^build"],
      "outputs": ["coverage/**"]
    },
    "clean": {
      "cache": false
    }
  }
}
```

### `apps/web/package.json`

```json
{
  "name": "@repo/web",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "build": "next build",
    "dev": "next dev --port 3000",
    "lint": "next lint && tsc --noEmit",
    "typecheck": "tsc --noEmit",
    "clean": "rm -rf .next node_modules"
  },
  "dependencies": {
    "next": "^15.0",
    "react": "^19.0",
    "react-dom": "^19.0",
    "@repo/ui": "workspace:*",
    "@tanstack/react-query": "^5.0",
    "zustand": "^5.0",
    "framer-motion": "^11.0",
    "gsap": "^3.12",
    "@react-three/fiber": "^8.0",
    "@react-three/drei": "^9.0",
    "@react-three/postprocessing": "^2.0",
    "three": "^0.165",
    "@rive-app/react-canvas": "latest",
    "@tremor/react": "^3.0",
    "@stripe/stripe-js": "latest"
  },
  "devDependencies": {
    "@repo/tsconfig": "workspace:*",
    "@repo/eslint-config": "workspace:*",
    "typescript": "^5.5",
    "tailwindcss": "^4.0",
    "@types/react": "^19.0",
    "@types/three": "latest",
    "@next/bundle-analyzer": "latest"
  }
}
```

### `apps/api/package.json` (Python shim)

This is the trick for polyglot monorepos — a `package.json` that wraps Python
commands so Turborepo can orchestrate them:

```json
{
  "name": "@repo/api",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "dev": "uvicorn saas.main:app --reload --host 0.0.0.0 --port 8000",
    "build": "echo 'Python — no build step'",
    "lint": "ruff check saas/ && ruff check ../../pipeline/",
    "test": "python -m pytest ../../tests/ -v",
    "typecheck": "pyright saas/",
    "worker": "celery -A saas.workers.celery_app worker -Q video,video_priority -c 2 --loglevel=info",
    "worker:beat": "celery -A saas.workers.celery_app beat --loglevel=info",
    "worker:flower": "celery -A saas.workers.celery_app flower --port=5555",
    "db:migrate": "alembic upgrade head",
    "db:make-migration": "alembic revision --autogenerate -m",
    "clean": "find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true"
  }
}
```

### `packages/ui/package.json`

```json
{
  "name": "@repo/ui",
  "version": "0.0.0",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "lint": "eslint . --max-warnings 0",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@radix-ui/react-dialog": "latest",
    "@radix-ui/react-dropdown-menu": "latest",
    "@radix-ui/react-slot": "latest",
    "class-variance-authority": "latest",
    "clsx": "latest",
    "tailwind-merge": "latest"
  },
  "devDependencies": {
    "@repo/tsconfig": "workspace:*",
    "@repo/eslint-config": "workspace:*",
    "typescript": "^5.5",
    "react": "^19.0"
  }
}
```

---

## Development Workflow

```bash
# Initial setup
pnpm install                         # Install all JS deps
pip install -r requirements.txt -r requirements-saas.txt  # Python deps
docker compose up -d postgres redis  # Start infra

# Run everything
pnpm dev                             # Starts web (port 3000) + api (port 8000) in parallel

# Run only frontend
pnpm dev:web

# Run only API
pnpm dev:api

# Run workers (separate terminal)
cd apps/api && pnpm worker

# Run all tests
pnpm test                            # JS tests + Python tests via turbo

# Run only Python tests
cd apps/api && pnpm test

# Lint everything
pnpm lint                            # ESLint (JS) + Ruff (Python) via turbo

# Database migrations
pnpm db:migrate
pnpm db:make-migration "add_new_table"
```

---

## Docker Build from Monorepo

Docker builds use the **root context** with targeted Dockerfiles:

```bash
# Build API image
docker build -f docker/Dockerfile.api -t shortfactory-api .

# Build worker image
docker build -f docker/Dockerfile.worker -t shortfactory-worker .

# Build web image (or deploy to Vercel)
docker build -f docker/Dockerfile.web -t shortfactory-web .
```

The Dockerfiles use multi-stage builds and only copy the relevant `apps/` and
`packages/` directories to keep images small.

---

## Vercel Deployment (Frontend)

The Next.js frontend (`apps/web/`) deploys to Vercel with monorepo support:

1. Connect the repo to Vercel
2. Set **Root Directory** to `apps/web`
3. Vercel auto-detects Turborepo and uses remote caching
4. Build command: `cd ../.. && pnpm turbo run build --filter=@repo/web`
5. Output directory: `apps/web/.next`

Vercel + Turborepo remote caching means CI builds only rebuild what changed.

---

## Remote Caching (CI Speedup)

Enable Turborepo Remote Cache for 2-5x faster CI:

```bash
# Link repo to Vercel for remote caching
npx turbo login
npx turbo link
```

Or self-host with `turbo-remote-cache-rs` (Rust, very fast).

In GitHub Actions:
```yaml
- name: Setup Turbo Cache
  uses: actions/cache@v4
  with:
    path: .turbo
    key: turbo-${{ runner.os }}-${{ github.sha }}
    restore-keys: turbo-${{ runner.os }}-
```

---

## Migration Path

Since the repo currently has `pipeline/` at the root with no monorepo structure,
the migration is:

1. Initialize pnpm + Turborepo at root
2. Create `apps/web/` — scaffold Next.js project
3. Create `apps/api/` — move `saas/` code here (or symlink)
4. Create `packages/` — extract shared configs
5. Keep `pipeline/` at root — it's consumed by both CLI and `apps/api/`
6. Update Docker contexts to build from root
7. Update CI to use `pnpm` and `turbo`

The existing `pipeline/` package and `tests/` directory stay in place. Only new
SaaS code goes into the `apps/` and `packages/` structure.
