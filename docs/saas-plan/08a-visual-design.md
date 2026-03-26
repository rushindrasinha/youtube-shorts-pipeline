# 08a — Visual Design System & Animation Architecture

## Design Philosophy

ShortFactory makes videos. The brand identity should **feel** like video —
color, motion, energy, depth. Think cinema control room meets futuristic
content studio. Not flat SaaS template. Not AI slop gradients.

**Three principles:**
1. **Dark-first, light-on-demand** — Video production happens on dark interfaces. Dark backgrounds let accent colors pop and create cinematic depth.
2. **One hero, everything else supports it** — A single 3D focal point (the landing hero). Everything else uses 2D animation executed with restraint. Linear.app looks stunning not because they put 3D everywhere, but because one effect is done *perfectly*.
3. **Motion has meaning** — Every animation communicates state (loading, progress, completion). No decorative animation that doesn't serve UX. If something moves, it tells you something.

---

## Color System

```
Background tiers:
  --bg-root:       #09090b    (near-black, Zinc 950)
  --bg-surface:    #18181b    (card backgrounds, Zinc 900)
  --bg-elevated:   #27272a    (modals, dropdowns, Zinc 800)

Text:
  --text-primary:  #fafafa    (Zinc 50)
  --text-secondary:#a1a1aa    (Zinc 400)
  --text-muted:    #71717a    (Zinc 500)

Accent gradient (the ShortFactory signature):
  --accent-from:   #7c3aed    (Violet 600)
  --accent-via:    #2563eb    (Blue 600)
  --accent-to:     #06b6d4    (Cyan 500)

  Used as: background: linear-gradient(135deg, var(--accent-from), var(--accent-via), var(--accent-to));
  This gradient appears on: hero light spills, progress bars, active nav items,
  CTA buttons, focus rings. It is the only gradient — consistency > variety.

Status colors:
  --status-success:  #22c55e  (Green 500)
  --status-warning:  #f59e0b  (Amber 500)
  --status-error:    #ef4444  (Red 500)
  --status-info:     #3b82f6  (Blue 500)
  --status-running:  #a78bfa  (Violet 400, animated pulse)

Border:
  --border-subtle:   rgba(255, 255, 255, 0.06)
  --border-visible:  rgba(255, 255, 255, 0.12)
```

### Why These Colors

The violet→blue→cyan gradient reflects the pipeline concept: creative input (warm violet)
flows through AI processing (blue) into polished output (cool cyan). It's not random —
it maps to the product metaphor.

---

## Typography

```
Display / Hero:      Space Grotesk, 700 weight
                     Used for: landing page headlines, pricing tier names
                     Sizes: 64px (hero), 48px (section), 36px (subsection)
                     Letter-spacing: -0.02em (tight, modern)

UI / Body:           Inter, 400/500/600
                     Used for: everything in the dashboard
                     Sizes: 14px (body), 13px (secondary), 12px (caption), 16px (emphasis)

Mono:                JetBrains Mono, 400
                     Used for: API keys, code snippets, job IDs
                     Size: 13px
```

Load via `next/font` — zero layout shift, self-hosted:
```tsx
import { Space_Grotesk, Inter, JetBrains_Mono } from 'next/font/google'
```

---

## Animation Stack

| Layer | Library | Version | Purpose | Bundle Cost |
|-------|---------|---------|---------|-------------|
| **3D Hero** | `@react-three/fiber` + `drei` + `postprocessing` | 8.x / 9.x / 2.x | One cinematic landing hero scene | ~200KB (lazy chunk) |
| **Scroll orchestration** | `gsap` + `ScrollTrigger` | 3.12+ | Drive 3D scene + section parallax on scroll | ~25KB |
| **UI animation** | `framer-motion` | 11+ | Page transitions, element entrances, hover, layout | ~35KB |
| **Micro-interactions** | `@rive-app/react-canvas` | Latest | Pipeline stage icons, loading states, empty states | ~80KB WASM runtime |
| **Ambient effects** | Pure CSS | N/A | Gradients, glassmorphism, blurred orbs, tilt | 0KB |
| **Charts** | `tremor` | 3.x | Usage charts, analytics (built on Tailwind) | Tree-shakeable |

### Critical: Dynamic Import Pattern for 3D

Three.js must **never** be in the main bundle. It must be dynamically imported with SSR
disabled and a graceful fallback:

```tsx
// app/page.tsx (landing)
import dynamic from 'next/dynamic'

const HeroScene = dynamic(() => import('@/components/landing/hero-scene'), {
  ssr: false,
  loading: () => <HeroFallback />,   // Static gradient while 3D loads
})
```

```tsx
// components/landing/hero-fallback.tsx
export function HeroFallback() {
  return (
    <div className="relative h-screen overflow-hidden bg-[#09090b]">
      {/* Animated CSS mesh gradient — looks great, costs nothing */}
      <div className="absolute inset-0">
        <div className="absolute w-[60vw] h-[60vw] rounded-full blur-[120px] opacity-20
                        bg-violet-600 -top-[20%] -left-[10%]
                        animate-[float_20s_ease-in-out_infinite]" />
        <div className="absolute w-[50vw] h-[50vw] rounded-full blur-[120px] opacity-15
                        bg-blue-600 -bottom-[20%] -right-[10%]
                        animate-[float_20s_ease-in-out_infinite_-10s]" />
      </div>
    </div>
  )
}
```

### Mobile Strategy

Mobile devices cannot handle WebGL reliably. Detect and serve a stripped experience:

```tsx
const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
const isLowEnd = typeof navigator !== 'undefined' && (navigator.hardwareConcurrency ?? 8) <= 4

// Mobile: show HeroFallback (CSS only) + hero text + CTA
// Low-end: same as mobile
// Desktop: full R3F scene
```

---

## Landing Page — Section-by-Section Design

### Section 1: Hero (viewport height, scroll-driven)

**Concept:** A 3D visualization of the ShortFactory pipeline. As the user scrolls,
a topic (floating 3D text) transforms through the pipeline stages — research particles
gather, a script materializes, image frames render, sound waves pulse, and everything
assembles into a phone screen showing a finished Short.

**Technical approach:**
- R3F canvas, full viewport, absolute behind hero text
- GSAP ScrollTrigger with `scrub: 0.8` (smooth scroll-linked, not 1:1)
- Post-processing: bloom on accent-colored elements, chromatic aberration on transitions
- Geometry budget: <30K triangles total (the "impressiveness" comes from shaders + post-processing, not polygon count)
- `dpr={[1, 1.5]}` — cap pixel ratio for performance
- `frameloop="demand"` — only render on scroll events, not 60fps continuous

```tsx
// components/landing/hero-scene.tsx (conceptual structure)
import { Canvas } from '@react-three/fiber'
import { Float, Environment, Text3D } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'

export default function HeroScene() {
  return (
    <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 5], fov: 45 }}>
      <Environment preset="night" />

      {/* Pipeline stages — each animates in on scroll */}
      <PipelineVisualization />

      {/* Phone frame that assembles at the end */}
      <PhoneFrame />

      <EffectComposer>
        <Bloom luminanceThreshold={0.8} intensity={0.5} radius={0.4} />
      </EffectComposer>
    </Canvas>
  )
}
```

**Hero text overlay (HTML, positioned over canvas):**

```tsx
<div className="relative z-10 flex flex-col items-center justify-center h-screen px-6">
  <h1 className="font-display text-6xl md:text-7xl font-bold text-center
                  tracking-tight text-white max-w-4xl">
    Topic in.{' '}
    <span className="bg-gradient-to-r from-violet-400 via-blue-400 to-cyan-400
                     bg-clip-text text-transparent">
      Short out.
    </span>
  </h1>
  <p className="mt-6 text-lg text-zinc-400 max-w-xl text-center">
    AI-powered YouTube Shorts pipeline. From trending topic to published
    video in under 3 minutes.
  </p>
  <div className="mt-10 flex gap-4">
    <Button size="lg" className="bg-gradient-to-r from-violet-600 to-blue-600
                                  hover:from-violet-500 hover:to-blue-500
                                  text-white shadow-lg shadow-violet-500/25">
      Start Free
    </Button>
    <Button size="lg" variant="outline" className="border-zinc-700 text-zinc-300">
      See it in action
    </Button>
  </div>
</div>
```

### Section 2: Pipeline Showcase ("How it works")

**Concept:** A horizontal sequence of 8 pipeline stages, each with a Rive-animated
icon that activates when scrolled into view. Connected by a flowing gradient line.

```
  [Topic] ──→ [Research] ──→ [Script] ──→ [Visuals] ──→ [Voice] ──→ [Captions] ──→ [Music] ──→ [Upload]
```

**Technical approach:**
- Each stage card: glassmorphic container with Rive animation inside
- The connecting line is an SVG `<path>` with a gradient stroke that animates via GSAP
- Cards stagger-enter with Framer Motion `whileInView`:

```tsx
<motion.div
  initial={{ opacity: 0, y: 30 }}
  whileInView={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.6, delay: index * 0.1, ease: [0.16, 1, 0.3, 1] }}
  viewport={{ once: true, margin: '-80px' }}
>
  <StageCard stage={stage} />
</motion.div>
```

**Rive animations (`.riv` files, ~10-30KB each):**
- Research: magnifying glass scanning text particles
- Script: typewriter cursor flowing text
- Visuals: image frame crystallizing from pixels
- Voice: sound wave pulsing
- Captions: text appearing word-by-word (mirrors the actual product feature)
- Music: equalizer bars dancing
- Upload: arrow lifting into cloud

These animations are **interactive state machines** in Rive — they respond to hover
(play faster) and scroll position (advance timeline). Not just looping GIFs.

### Section 3: Feature Deep-Dive

**Concept:** Three large feature cards, each showing a specific capability with an
embedded UI mockup that animates.

1. **"Word-by-word captions"** — Shows an actual ASS-style caption animation playing
   in a phone mockup. Yellow highlight bouncing word to word. This is the killer feature
   and we demo it live in the browser, not a video.

2. **"Trending topic discovery"** — Shows a live-updating feed of real trending topics
   (from our cached API data) with scores and sources. "Not a mockup — these are real
   trending topics right now."

3. **"One-click to YouTube"** — Shows the pipeline progress UI with stages completing
   in real-time. Animated with Framer Motion springs.

**Card style (glassmorphic):**

```css
.feature-card {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px) saturate(1.3);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.03) inset,
    0 25px 50px -12px rgba(0, 0, 0, 0.4);
  transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1),
              box-shadow 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.feature-card:hover {
  transform: perspective(800px) rotateY(-2deg) rotateX(2deg) translateY(-4px);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.06) inset,
    0 30px 60px -15px rgba(124, 58, 237, 0.15);
}
```

### Section 4: Live Demo / Social Proof

**Concept:** A counter showing real stats, animated with spring physics.

```
  [12,847 videos created]   [94.7% success rate]   [$0.11 avg cost]
```

Numbers animate from 0 on viewport entry using Framer Motion's `useSpring` +
`useInView`. Below: logos of YouTube channels using the platform (when available)
or testimonial cards.

### Section 5: Pricing

**Concept:** Four plan cards. The recommended plan ("Pro") is elevated with the accent
gradient border. All cards enter with staggered perspective rotation:

```tsx
<motion.div
  initial={{ opacity: 0, rotateX: -10, y: 40 }}
  whileInView={{ opacity: 1, rotateX: 0, y: 0 }}
  transition={{ duration: 0.7, delay: index * 0.12, ease: [0.16, 1, 0.3, 1] }}
  viewport={{ once: true }}
  style={{ perspective: 1000 }}
>
  <PricingCard plan={plan} recommended={plan.name === 'pro'} />
</motion.div>
```

Recommended card has an animated gradient border:

```css
.pricing-recommended {
  position: relative;
  background: var(--bg-surface);
  border-radius: 16px;
}
.pricing-recommended::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 17px;
  background: linear-gradient(135deg, #7c3aed, #2563eb, #06b6d4);
  background-size: 200% 200%;
  animation: borderShift 4s ease infinite;
  z-index: -1;
}
@keyframes borderShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
```

### Section 6: CTA + Footer

**Concept:** Full-width CTA section with the mesh gradient background (pure CSS,
same technique as the hero fallback). Below: clean footer with nav links.

```css
.cta-section {
  position: relative;
  overflow: hidden;
  padding: 120px 0;
}

.cta-section::before,
.cta-section::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  animation: float 20s ease-in-out infinite;
}

.cta-section::before {
  width: 50vw; height: 50vw;
  background: rgba(124, 58, 237, 0.15);
  top: -30%; left: -10%;
}

.cta-section::after {
  width: 40vw; height: 40vw;
  background: rgba(6, 182, 212, 0.1);
  bottom: -30%; right: -10%;
  animation-delay: -10s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}
```

---

## Dashboard Animation Patterns

The dashboard is NOT the landing page. Animations here must be fast, functional,
and never block user interaction.

### Job Progress Ring

A circular progress indicator driven by Framer Motion spring:

```tsx
import { motion, useSpring, useTransform } from 'framer-motion'

function ProgressRing({ percent }: { percent: number }) {
  const spring = useSpring(0, { stiffness: 60, damping: 15 })
  const circumference = 2 * Math.PI * 45
  const strokeDashoffset = useTransform(spring, (v) => circumference * (1 - v / 100))

  useEffect(() => { spring.set(percent) }, [percent])

  return (
    <svg width="100" height="100" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r="45" fill="none"
              stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
      <motion.circle cx="50" cy="50" r="45" fill="none"
              stroke="url(#gradient)" strokeWidth="6"
              strokeDasharray={circumference}
              style={{ strokeDashoffset }}
              strokeLinecap="round"
              transform="rotate(-90 50 50)" />
      <defs>
        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
    </svg>
  )
}
```

### Stage List Animation

Pipeline stages stagger in as they complete:

```tsx
<AnimatePresence mode="popLayout">
  {stages.map((stage, i) => (
    <motion.div
      key={stage.name}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.05 }}
      layout
    >
      <StageRow stage={stage} />
    </motion.div>
  ))}
</AnimatePresence>
```

### Video Card Hover

Subtle lift + shadow increase. No 3D transforms in the dashboard — keep it clean:

```tsx
<motion.div
  whileHover={{ y: -2, boxShadow: '0 20px 40px -12px rgba(0,0,0,0.3)' }}
  transition={{ duration: 0.2 }}
>
  <VideoCard video={video} />
</motion.div>
```

### Page Transitions

Framer Motion `AnimatePresence` wraps the dashboard layout:

```tsx
// (dashboard)/layout.tsx
<AnimatePresence mode="wait">
  <motion.main
    key={pathname}
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -8 }}
    transition={{ duration: 0.2 }}
  >
    {children}
  </motion.main>
</AnimatePresence>
```

---

## Performance Budget

| Metric | Target | Measured By |
|--------|--------|-------------|
| First-load JS (landing) | < 150KB (before 3D chunk) | `next/bundle-analyzer` |
| 3D chunk (lazy) | < 250KB gzipped | Isolated dynamic import |
| LCP | < 2.5s | Lighthouse |
| CLS | < 0.1 | Lighthouse |
| FID | < 100ms | Lighthouse |
| Hero 3D FPS | 60fps desktop / N/A mobile | Chrome DevTools Performance |
| Total page weight (landing) | < 1MB first load | Network tab |

### Optimization Checklist

- [ ] Three.js dynamically imported with `ssr: false`
- [ ] `@react-three/drei` uses named imports only (tree-shaking)
- [ ] 3D models use Draco compression (`.glb` files, 80-90% smaller)
- [ ] Textures use KTX2/Basis Universal format
- [ ] Canvas renders at `dpr={[1, 1.5]}`, never full Retina
- [ ] `frameloop="demand"` — 3D renders only on scroll/interaction
- [ ] Rive `.riv` files loaded lazily per section
- [ ] All fonts loaded via `next/font` (zero FOUT)
- [ ] Images use `<Image>` component with `priority` on above-fold
- [ ] Mobile gets CSS-only fallback (no WebGL)
- [ ] `@next/bundle-analyzer` verified: Three.js in its own chunk

---

## Component Directory Structure

```
frontend/src/components/
  landing/
    hero-scene.tsx              # R3F canvas + pipeline visualization
    hero-fallback.tsx           # CSS gradient fallback (mobile + loading)
    pipeline-showcase.tsx       # "How it works" section with Rive icons
    feature-cards.tsx           # Glassmorphic deep-dive cards
    live-stats.tsx              # Animated counter section
    pricing-section.tsx         # Plan cards with stagger entrance
    cta-section.tsx             # Final CTA with mesh gradient bg
    stage-rive.tsx              # Rive wrapper for pipeline stage icons
  motion/
    fade-in.tsx                 # Reusable whileInView fade-in wrapper
    stagger-children.tsx        # Stagger container for lists
    progress-ring.tsx           # Circular progress (dashboard)
    animated-number.tsx         # Spring-animated counter
    page-transition.tsx         # Route transition wrapper
  3d/
    pipeline-visualization.tsx  # The main 3D pipeline geometry
    phone-frame.tsx             # 3D phone model for hero
    shaders/
      gradient-mesh.glsl        # Custom shader for aurora/gradient effects
```
