# 08 — Frontend (Next.js)

## Technology Stack

| Technology | Purpose |
|-----------|---------|
| Next.js 15+ (App Router) | Framework, SSR, routing |
| TypeScript | Type safety |
| Tailwind CSS | Utility-first styling |
| shadcn/ui | Component library (Radix primitives + Tailwind) |
| TanStack Query (React Query) | Server state management, caching |
| Zustand | Client state (auth, UI) |
| React Three Fiber + drei + postprocessing | 3D cinematic landing hero (see [08a-visual-design](08a-visual-design.md)) |
| GSAP + ScrollTrigger | Scroll-driven 3D animations + section transitions |
| Framer Motion | UI animations (page transitions, entrances, hover) |
| Rive (`@rive-app/react-canvas`) | Interactive micro-animations (pipeline icons, loading) |
| Tremor | Analytics charts (built on Tailwind, matches shadcn) |
| Stripe.js | Payment UI |

> **Visual design system:** See [08a-visual-design.md](08a-visual-design.md) for the
> complete color system, typography, animation architecture, landing page
> section-by-section design, performance budgets, and component patterns.

---

## Page Structure

```
frontend/
  src/
    app/
      layout.tsx                    # Root layout (nav, auth provider)
      page.tsx                      # Landing page (marketing)
      (auth)/
        login/page.tsx              # Email/password + social login
        register/page.tsx           # Registration
        callback/page.tsx           # OAuth callback handler
        forgot-password/page.tsx
      (dashboard)/
        layout.tsx                  # Dashboard layout (sidebar, nav)
        page.tsx                    # Dashboard home (recent jobs, stats)
        jobs/
          page.tsx                  # Job list (filterable, sortable)
          new/page.tsx              # Create new video job
          [id]/page.tsx             # Job detail + real-time progress
        videos/
          page.tsx                  # Video library
          [id]/page.tsx             # Video detail (preview, download, edit metadata)
        topics/
          page.tsx                  # Trending topics browser
        channels/
          page.tsx                  # YouTube channel management
          connect/page.tsx          # YouTube OAuth flow
        teams/
          page.tsx                  # Team management (agency)
          [id]/page.tsx             # Team detail + members
          [id]/invite/page.tsx      # Invite member
        settings/
          page.tsx                  # User preferences (voice, style, language)
          api-keys/page.tsx         # API key management
          provider-keys/page.tsx    # BYOK key management
        billing/
          page.tsx                  # Current plan, usage, invoices
          plans/page.tsx            # Plan comparison + upgrade
          success/page.tsx          # Post-checkout success
      (admin)/
        layout.tsx                  # Admin layout
        page.tsx                    # Admin dashboard (system stats)
        users/page.tsx              # User management
        jobs/page.tsx               # All jobs (global view)
    components/
      ui/                           # shadcn/ui components (button, card, dialog, etc.)
      landing/                      # Landing page 3D + animation components
        hero-scene.tsx              # R3F canvas (dynamic import, ssr: false)
        hero-fallback.tsx           # CSS gradient fallback (mobile + loading)
        pipeline-showcase.tsx       # "How it works" with Rive icons
        feature-cards.tsx           # Glassmorphic deep-dive cards
        pricing-section.tsx         # Plan cards with stagger entrance
        cta-section.tsx             # CTA with mesh gradient background
      motion/                       # Reusable animation primitives
        fade-in.tsx                 # whileInView fade-in wrapper
        stagger-children.tsx        # Stagger container for lists
        progress-ring.tsx           # Circular progress (dashboard)
        animated-number.tsx         # Spring-animated counter
        page-transition.tsx         # Route transition wrapper
      3d/                           # Three.js geometry (lazy-loaded)
        pipeline-visualization.tsx  # Main 3D pipeline geometry
        phone-frame.tsx             # 3D phone model for hero
      layout/
        sidebar.tsx                 # Dashboard sidebar navigation
        header.tsx                  # Top navigation bar
        footer.tsx                  # Marketing footer
      jobs/
        job-card.tsx                # Job summary card for list view
        job-progress.tsx            # Real-time progress component (WebSocket)
        job-stages.tsx              # Stage-by-stage progress indicators
        create-job-form.tsx         # New video creation form
      videos/
        video-card.tsx              # Video thumbnail card
        video-player.tsx            # In-browser video preview
        video-actions.tsx           # Download, upload to YouTube, delete
      topics/
        topic-card.tsx              # Trending topic card with "Create" button
        topic-list.tsx              # Scrollable topic list
      channels/
        channel-card.tsx            # YouTube channel card
        connect-button.tsx          # OAuth connect button
      teams/
        member-list.tsx             # Team member list with roles
        invite-form.tsx             # Invite member form
      billing/
        plan-card.tsx               # Plan comparison card
        usage-bar.tsx               # Usage progress bar
        invoice-list.tsx            # Invoice history
      shared/
        loading-spinner.tsx
        error-boundary.tsx
        pagination.tsx
        empty-state.tsx
        confirm-dialog.tsx
    lib/
      api.ts                        # API client (fetch wrapper with auth)
      auth.ts                       # Auth context, token management
      websocket.ts                  # WebSocket connection manager
      stripe.ts                     # Stripe.js initialization
      utils.ts                      # Shared utilities
    hooks/
      use-auth.ts                   # Auth state hook
      use-job-progress.ts           # WebSocket job progress hook
      use-jobs.ts                   # React Query hooks for jobs
      use-videos.ts                 # React Query hooks for videos
      use-billing.ts                # React Query hooks for billing
    types/
      api.ts                        # API response types (mirrors backend schemas)
      job.ts
      video.ts
      user.ts
      billing.ts
```

---

## Key Pages — Detailed Design

### 1. Landing Page (`/`)

See [08a-visual-design.md](08a-visual-design.md) for the full section-by-section
design with 3D hero, Rive animations, glassmorphic cards, and performance budgets.

Summary:
- **Hero:** 3D pipeline visualization (R3F) — topic transforms into visual frames → assembles into phone screen. Scroll-driven via GSAP. "Topic in. Short out."
- **Pipeline showcase:** 8 Rive-animated stage icons connected by gradient SVG line
- **Feature deep-dive:** 3 glassmorphic cards with live UI mockups (captions demo, trending topics, progress UI)
- **Stats:** Animated counters (spring physics) for videos created, success rate, avg cost
- **Pricing:** 4 plan cards with perspective entrance animations, recommended plan has animated gradient border
- **CTA + Footer:** Mesh gradient background (pure CSS), "Start Free" button

### 2. Dashboard (`/dashboard`)

```
┌─────────────────────────────────────────────────┐
│  ShortFactory          [user avatar] [Settings]  │
├────────┬────────────────────────────────────────┤
│        │                                         │
│  [icon] │  Good morning, John!                   │
│ Dashboard│                                       │
│  [icon] │  ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  Jobs   │  │ 12 / 30 │ │ 3 Active│ │ $0.11   │ │
│  [icon] │  │ Videos   │ │ Jobs    │ │ Avg Cost│ │
│  Videos │  └─────────┘ └─────────┘ └─────────┘ │
│  [icon] │                                       │
│ Trending│  Recent Jobs                          │
│  [icon] │  ┌────────────────────────────────┐   │
│ Channels│  │ [thumb] SpaceX Topic  ██████ 72% │  │
│  [icon] │  │ [thumb] AI Advances   ✓ Done    │  │
│  Teams  │  │ [thumb] Climate News  ✓ Done    │  │
│  [icon] │  └────────────────────────────────┘   │
│ Settings│                                       │
│  [icon] │  Quick Actions                        │
│ Billing │  [+ New Video]  [Browse Trending]     │
│         │                                       │
└────────┴────────────────────────────────────────┘
```

### 3. Create New Video (`/dashboard/jobs/new`)

```
┌──────────────────────────────────────────┐
│  Create New Video                         │
│                                           │
│  Topic *                                  │
│  ┌──────────────────────────────────────┐ │
│  │ SpaceX successfully lands Starship   │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  Channel Context (optional)               │
│  ┌──────────────────────────────────────┐ │
│  │ Tech news channel, energetic style   │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  ── Advanced Settings ──────────────────  │
│                                           │
│  Language    [English ▼]                  │
│  Voice       [George (Default) ▼]        │
│  Caption     [Yellow Highlight ▼] [PRO]  │
│  Music       [Auto-match ▼]              │
│                                           │
│  YouTube Channel  [My Tech Channel ▼]    │
│  □ Auto-upload after generation           │
│  Privacy   [Private ▼]                   │
│                                           │
│  □ Schedule for later                     │
│  [Date picker]  [Time picker]            │
│                                           │
│  [Create Video]     Cost: ~$0.11         │
│  ─── or ───                               │
│  [Browse Trending Topics]                 │
└──────────────────────────────────────────┘
```

### 4. Job Progress (`/dashboard/jobs/{id}`)

Real-time progress with WebSocket updates:

```
┌──────────────────────────────────────────┐
│  ← Back to Jobs                           │
│                                           │
│  SpaceX successfully lands Starship       │
│  Status: Generating...  ████████░░ 65%    │
│                                           │
│  Pipeline Stages                          │
│  ✓ Research     2.1s                      │
│  ✓ Script       3.5s                      │
│  ✓ B-Roll       12.0s                     │
│  ✓ Voiceover    8.2s                      │
│  ● Captions     running...                │
│  ○ Music                                  │
│  ○ Assembly                               │
│  ○ Thumbnail                              │
│                                           │
│  ── Preview ──                            │
│  Script:                                  │
│  "Did you know SpaceX just pulled off..." │
│                                           │
│  B-Roll Frames:                           │
│  [img1] [img2] [img3]                     │
│                                           │
│  Estimated completion: ~45 seconds        │
└──────────────────────────────────────────┘
```

### 5. Video Library (`/dashboard/videos`)

```
┌──────────────────────────────────────────┐
│  My Videos (47 total)                     │
│  [Search...] [Filter: All ▼] [Sort ▼]    │
│                                           │
│  ┌─────┐  SpaceX Lands Starship!         │
│  │thumb│  72.5s · 1080x1920 · Mar 25     │
│  │     │  ✓ Uploaded to YouTube           │
│  └─────┘  [Preview] [Download] [⋮]       │
│                                           │
│  ┌─────┐  AI Revolution 2026             │
│  │thumb│  65.2s · 1080x1920 · Mar 24     │
│  │     │  ⏳ Not uploaded                 │
│  └─────┘  [Preview] [Download] [Upload] [⋮]│
│                                           │
│  ┌─────┐  Climate Summit Results         │
│  │thumb│  81.0s · 1080x1920 · Mar 23     │
│  │     │  ✓ Uploaded · 12.3K views       │
│  └─────┘  [Preview] [Download] [⋮]       │
│                                           │
│  [Load more...]                           │
└──────────────────────────────────────────┘
```

### 6. Trending Topics (`/dashboard/topics`)

```
┌──────────────────────────────────────────┐
│  Trending Topics                          │
│  Last updated: 3 min ago [Refresh]        │
│                                           │
│  ┌────────────────────────────────────┐   │
│  │ 🔥 0.92  SpaceX Starship Lands    │   │
│  │  reddit/r/technology · 45.2K ⬆    │   │
│  │  [Create Video]                    │   │
│  ├────────────────────────────────────┤   │
│  │ 🔥 0.87  New AI Regulation in EU  │   │
│  │  google_trends · Trending          │   │
│  │  [Create Video]                    │   │
│  ├────────────────────────────────────┤   │
│  │ 🔥 0.81  iPhone 18 Leaks          │   │
│  │  rss/Hacker News · 312 points     │   │
│  │  [Create Video]                    │   │
│  └────────────────────────────────────┘   │
│                                           │
│  [Let AI Pick Best Topic]                 │
└──────────────────────────────────────────┘
```

### 7. Billing (`/dashboard/billing`)

```
┌──────────────────────────────────────────┐
│  Billing & Usage                          │
│                                           │
│  Current Plan: Creator ($19/mo)           │
│  [Upgrade]  [Manage on Stripe]            │
│                                           │
│  This Month's Usage                       │
│  ██████████████░░░░░░░░  12 / 30 videos   │
│  18 remaining · Resets Apr 1              │
│                                           │
│  Cost Breakdown                           │
│  API costs:    $1.32                      │
│  Your plan:    $19.00/mo                  │
│  Cost/video:   $0.11 avg                  │
│                                           │
│  ── Compare Plans ──                      │
│  [Free]     [Creator ✓] [Pro]  [Agency]   │
│   3/mo       30/mo      100/mo  500/mo    │
│   $0         $19        $49     $149      │
│                                           │
│  Recent Invoices                          │
│  Mar 2026  $19.00  Paid  [Download]       │
│  Feb 2026  $19.00  Paid  [Download]       │
└──────────────────────────────────────────┘
```

### 8. Team Management (`/dashboard/teams/{id}`) — Agency Feature

```
┌──────────────────────────────────────────┐
│  Awesome Agency                           │
│  5 members · 3 channels · 47 videos      │
│                                           │
│  Members                                  │
│  ┌────────────────────────────────────┐   │
│  │ [avatar] John Doe     Owner       │   │
│  │ [avatar] Jane Smith   Admin  [⋮]  │   │
│  │ [avatar] Bob Jones    Member [⋮]  │   │
│  │ [avatar] Pending...   Invited     │   │
│  └────────────────────────────────────┘   │
│  [+ Invite Member]                        │
│                                           │
│  Shared Channels                          │
│  [thumb] Tech Daily   · 12 uploads       │
│  [thumb] News Flash   · 8 uploads        │
│  [thumb] AI Updates   · 27 uploads       │
│                                           │
│  Team Activity                            │
│  Today: 3 videos created                  │
│  This week: 14 videos created             │
└──────────────────────────────────────────┘
```

---

## Real-Time Job Progress Hook

```typescript
// frontend/src/hooks/use-job-progress.ts

import { useEffect, useState, useRef } from 'react'

interface StageProgress {
  type: string
  stage: string
  progress_pct: number
  timestamp: string
}

export function useJobProgress(jobId: string, token: string) {
  const [progress, setProgress] = useState<StageProgress | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!jobId || !token) return

    const ws = new WebSocket(
      `${process.env.NEXT_PUBLIC_WS_URL}/ws/jobs/${jobId}?token=${token}`
    )

    ws.onopen = () => setConnected(true)

    ws.onmessage = (event) => {
      const data: StageProgress = JSON.parse(event.data)
      setProgress(data)
    }

    ws.onclose = () => setConnected(false)

    wsRef.current = ws

    return () => {
      ws.close()
    }
  }, [jobId, token])

  return { progress, connected }
}
```

---

## API Client

```typescript
// frontend/src/lib/api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

class ApiClient {
  private accessToken: string | null = null

  setToken(token: string) {
    this.accessToken = token
  }

  private async fetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    }

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    })

    if (response.status === 401) {
      // Try refresh token
      await this.refreshToken()
      // Retry
      headers['Authorization'] = `Bearer ${this.accessToken}`
      const retry = await fetch(`${API_BASE}${path}`, { ...options, headers })
      if (!retry.ok) throw new ApiError(retry)
      return retry.json()
    }

    if (!response.ok) throw new ApiError(response)
    return response.json()
  }

  // Jobs
  createJob(data: CreateJobRequest) {
    return this.fetch<Job>('/jobs', { method: 'POST', body: JSON.stringify(data) })
  }

  listJobs(params?: { status?: string; limit?: number; cursor?: string }) {
    const query = new URLSearchParams(params as any).toString()
    return this.fetch<PaginatedResponse<Job>>(`/jobs?${query}`)
  }

  getJob(id: string) {
    return this.fetch<JobDetail>(`/jobs/${id}`)
  }

  // Videos
  listVideos(params?: { limit?: number; cursor?: string }) {
    const query = new URLSearchParams(params as any).toString()
    return this.fetch<PaginatedResponse<Video>>(`/videos?${query}`)
  }

  getVideoDownloadUrl(id: string) {
    return this.fetch<{ url: string }>(`/videos/${id}/download`)
  }

  // Topics
  getTrendingTopics() {
    return this.fetch<TopicListResponse>('/topics/trending')
  }

  quickCreateFromTopic(topicTitle: string, channelId?: string) {
    return this.fetch<Job>('/topics/quick-create', {
      method: 'POST',
      body: JSON.stringify({ topic_title: topicTitle, channel_id: channelId }),
    })
  }

  // Billing
  getPlans() {
    return this.fetch<Plan[]>('/billing/plans')
  }

  createCheckout(plan: string) {
    return this.fetch<{ checkout_url: string }>('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan }),
    })
  }

  // ... other methods
}

export const api = new ApiClient()
```
