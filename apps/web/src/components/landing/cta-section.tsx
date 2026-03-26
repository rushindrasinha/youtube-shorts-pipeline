'use client'

import { Button } from '@repo/ui'
import { FadeIn } from '@/components/motion/fade-in'

export function CTASection() {
  return (
    <section className="relative py-24 sm:py-32 px-6 overflow-hidden">
      {/* Mesh gradient orbs */}
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute w-[50vw] h-[50vw] rounded-full -top-[30%] -left-[10%]"
          style={{
            background:
              'radial-gradient(circle, rgba(124,58,237,0.15) 0%, transparent 70%)',
            filter: 'blur(120px)',
            animation: 'float 20s ease-in-out infinite',
          }}
        />
        <div
          className="absolute w-[40vw] h-[40vw] rounded-full -bottom-[30%] -right-[10%]"
          style={{
            background:
              'radial-gradient(circle, rgba(6,182,212,0.1) 0%, transparent 70%)',
            filter: 'blur(120px)',
            animation: 'float 20s ease-in-out infinite -10s',
          }}
        />
      </div>

      <div className="relative z-10 max-w-3xl mx-auto text-center">
        <FadeIn>
          <h2 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-tight">
            Ready to automate your{' '}
            <span className="bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Shorts?
            </span>
          </h2>
          <p className="mt-6 text-lg text-zinc-400 max-w-xl mx-auto">
            Join thousands of creators using ShortFactory to produce
            high-quality YouTube Shorts on autopilot.
          </p>
          <div className="mt-10">
            <Button
              variant="primary"
              size="lg"
              className="shadow-lg shadow-violet-500/25 text-base px-8"
            >
              Start Free
            </Button>
          </div>
        </FadeIn>
      </div>
    </section>
  )
}
