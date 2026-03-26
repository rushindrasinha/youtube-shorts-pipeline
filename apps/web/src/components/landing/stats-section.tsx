'use client'

import { AnimatedNumber } from '@/components/motion/animated-number'
import { FadeIn } from '@/components/motion/fade-in'

const stats = [
  {
    target: 12847,
    decimals: 0,
    prefix: '',
    suffix: '+',
    label: 'Videos Created',
  },
  {
    target: 98.7,
    decimals: 1,
    prefix: '',
    suffix: '%',
    label: 'Success Rate',
  },
  {
    target: 0.11,
    decimals: 2,
    prefix: '$',
    suffix: '',
    label: 'Avg Cost per Video',
  },
]

export function StatsSection() {
  return (
    <section className="relative py-24 sm:py-32 px-6">
      <div className="max-w-4xl mx-auto">
        <FadeIn>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 text-center">
            {stats.map((stat) => (
              <div key={stat.label} className="space-y-2">
                <div className="text-4xl sm:text-5xl font-bold font-display bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
                  <AnimatedNumber
                    target={stat.target}
                    decimals={stat.decimals}
                    prefix={stat.prefix}
                    suffix={stat.suffix}
                  />
                </div>
                <div className="text-sm text-zinc-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </FadeIn>
      </div>
    </section>
  )
}
