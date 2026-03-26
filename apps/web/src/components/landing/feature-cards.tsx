'use client'

import { FadeIn } from '@/components/motion/fade-in'

const features = [
  {
    title: 'AI Script Writing',
    description:
      'Claude analyzes trending topics and writes engaging, viral-ready scripts with hooks, pacing, and CTAs built in.',
    visual: (
      <div className="mt-4 space-y-2 text-left">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-zinc-500">Generating script...</span>
        </div>
        <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-3 text-xs text-zinc-400 leading-relaxed">
          <span className="text-zinc-200">&quot;Did you know</span> that SpaceX
          just pulled off something that was considered impossible 10 years
          ago?&quot;
          <span className="inline-block w-0.5 h-3 bg-violet-400 animate-pulse ml-0.5 align-middle" />
        </div>
      </div>
    ),
  },
  {
    title: 'Cinematic Visuals',
    description:
      'AI-generated B-roll images perfectly matched to each script segment. Every frame is 1080x1920 and ready for Shorts.',
    visual: (
      <div className="mt-4 grid grid-cols-3 gap-2">
        {[
          'from-violet-900 to-indigo-900',
          'from-blue-900 to-cyan-900',
          'from-indigo-900 to-violet-900',
        ].map((gradient, i) => (
          <div
            key={i}
            className={`aspect-[9/16] rounded-lg bg-gradient-to-b ${gradient} border border-white/[0.06] flex items-center justify-center`}
          >
            <svg
              className="w-4 h-4 text-white/20"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
              />
            </svg>
          </div>
        ))}
      </div>
    ),
  },
  {
    title: 'Word-Level Captions',
    description:
      'Precisely timed captions with yellow highlight that bounces word-by-word. The style that drives engagement on Shorts.',
    visual: (
      <div className="mt-4 flex flex-col items-center">
        <div className="w-full rounded-lg bg-black/40 px-4 py-3 text-center">
          <span className="text-sm text-white font-medium">
            Did you{' '}
            <span className="bg-yellow-400 text-black px-1 rounded font-bold">
              know
            </span>{' '}
            that this changes
          </span>
        </div>
        <div className="mt-2 flex gap-1">
          {[0.2, 0.5, 0.8, 1, 0.7, 0.4].map((h, i) => (
            <div
              key={i}
              className="w-1 rounded-full bg-gradient-to-t from-violet-500 to-cyan-400"
              style={{ height: `${h * 20 + 4}px` }}
            />
          ))}
        </div>
      </div>
    ),
  },
]

export function FeatureCards() {
  return (
    <section className="relative py-24 sm:py-32 px-6">
      <div className="max-w-6xl mx-auto">
        <FadeIn>
          <h2 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold text-center text-white tracking-tight">
            Built for{' '}
            <span className="bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
              virality
            </span>
          </h2>
          <p className="mt-4 text-zinc-400 text-center text-lg max-w-2xl mx-auto">
            Every component of the pipeline is optimized for YouTube Shorts
            engagement.
          </p>
        </FadeIn>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <FadeIn key={feature.title} delay={index * 120} direction="up">
              <div
                className="group relative rounded-2xl bg-white/[0.03] backdrop-blur-sm border border-white/[0.06] p-6 transition-all duration-500 hover:-translate-y-1"
                style={{
                  boxShadow:
                    '0 0 0 1px rgba(255,255,255,0.03) inset, 0 25px 50px -12px rgba(0,0,0,0.4)',
                }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget
                  el.style.transform =
                    'perspective(800px) rotateY(-2deg) rotateX(2deg) translateY(-4px)'
                  el.style.boxShadow =
                    '0 0 0 1px rgba(255,255,255,0.06) inset, 0 30px 60px -15px rgba(124,58,237,0.15)'
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget
                  el.style.transform = ''
                  el.style.boxShadow =
                    '0 0 0 1px rgba(255,255,255,0.03) inset, 0 25px 50px -12px rgba(0,0,0,0.4)'
                }}
              >
                <h3 className="font-display text-lg font-semibold text-white">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
                  {feature.description}
                </p>
                {feature.visual}
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  )
}
