'use client'

import { Button } from '@repo/ui'
import { AnimatedNumber } from '@/components/motion/animated-number'
import { FadeIn } from '@/components/motion/fade-in'

export function HeroSection() {
  return (
    <section className="hero-bg relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-6">
      {/* Mesh gradient background orbs */}
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute w-[60vw] h-[60vw] rounded-full opacity-20 -top-[20%] -left-[10%]"
          style={{
            background: 'radial-gradient(circle, rgba(124,58,237,0.4) 0%, transparent 70%)',
            filter: 'blur(120px)',
            animation: 'float 20s ease-in-out infinite',
          }}
        />
        <div
          className="absolute w-[50vw] h-[50vw] rounded-full opacity-15 -bottom-[20%] -right-[10%]"
          style={{
            background: 'radial-gradient(circle, rgba(99,102,241,0.4) 0%, transparent 70%)',
            filter: 'blur(120px)',
            animation: 'float 20s ease-in-out infinite -10s',
          }}
        />
        <div
          className="absolute w-[40vw] h-[40vw] rounded-full opacity-10 top-[30%] right-[20%]"
          style={{
            background: 'radial-gradient(circle, rgba(6,182,212,0.4) 0%, transparent 70%)',
            filter: 'blur(100px)',
            animation: 'float 20s ease-in-out infinite -5s',
          }}
        />
      </div>

      {/* Hero content */}
      <div className="relative z-10 flex flex-col items-center justify-center max-w-4xl text-center">
        <FadeIn delay={0} direction="up">
          <h1 className="font-display text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight text-white">
            Topic in.{' '}
            <span className="bg-gradient-to-r from-violet-400 via-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Short out.
            </span>
          </h1>
        </FadeIn>

        <FadeIn delay={150} direction="up">
          <p className="mt-6 text-lg sm:text-xl text-zinc-400 max-w-xl">
            AI-powered YouTube Shorts pipeline. From trending topic to published
            video in under 3 minutes.
          </p>
        </FadeIn>

        <FadeIn delay={300} direction="up">
          <div className="mt-10 flex flex-col sm:flex-row gap-4">
            <Button
              variant="primary"
              size="lg"
              className="shadow-lg shadow-violet-500/25"
            >
              Start Free
            </Button>
            <Button variant="outline" size="lg">
              See How It Works
            </Button>
          </div>
        </FadeIn>

        {/* Phone mockup */}
        <FadeIn delay={500} direction="up">
          <div
            className="mt-16 relative w-[220px] h-[440px] mx-auto rounded-[2.5rem] border-2 border-white/10 bg-zinc-900/80 shadow-2xl shadow-violet-500/10 overflow-hidden"
            style={{
              transform: 'perspective(800px) rotateY(-3deg) rotateX(3deg)',
            }}
          >
            {/* Screen content mockup */}
            <div className="absolute inset-3 rounded-[2rem] bg-gradient-to-b from-zinc-800 to-zinc-900 overflow-hidden">
              <div className="absolute inset-0 flex flex-col items-center justify-center p-4">
                <div className="w-full h-3 bg-white/5 rounded-full mb-2" />
                <div className="w-3/4 h-3 bg-white/5 rounded-full mb-6" />
                <div className="w-16 h-16 rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </div>
                <div className="w-full space-y-2 mt-4">
                  <div className="w-full h-2 bg-white/5 rounded-full" />
                  <div className="w-5/6 h-2 bg-white/5 rounded-full" />
                  <div className="w-4/6 h-2 bg-white/5 rounded-full" />
                </div>
                {/* Caption preview */}
                <div className="absolute bottom-8 left-4 right-4">
                  <div className="bg-black/60 rounded-lg px-3 py-2 text-center">
                    <span className="text-[10px] text-white font-medium">
                      Did you <span className="bg-yellow-400 text-black px-0.5 rounded">know</span> that...
                    </span>
                  </div>
                </div>
              </div>
            </div>
            {/* Notch */}
            <div className="absolute top-3 left-1/2 -translate-x-1/2 w-16 h-4 bg-black rounded-full" />
          </div>
        </FadeIn>

        {/* Stats row */}
        <FadeIn delay={700} direction="up">
          <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-3xl font-bold text-white font-display">
                <AnimatedNumber target={12847} prefix="" suffix="+" />
              </div>
              <div className="text-sm text-zinc-500 mt-1">Videos Created</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-white font-display">
                <AnimatedNumber target={98.7} decimals={1} suffix="%" />
              </div>
              <div className="text-sm text-zinc-500 mt-1">Success Rate</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-white font-display">
                <AnimatedNumber target={0.11} decimals={2} prefix="$" />
              </div>
              <div className="text-sm text-zinc-500 mt-1">Avg Cost per Video</div>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  )
}
