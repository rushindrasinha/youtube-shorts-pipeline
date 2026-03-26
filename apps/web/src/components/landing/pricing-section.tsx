'use client'

import { Button } from '@repo/ui'
import { FadeIn } from '@/components/motion/fade-in'

const plans = [
  {
    name: 'Free',
    price: 0,
    period: '',
    videos: '3 videos / month',
    features: [
      '720p output',
      'Basic captions',
      '1 YouTube channel',
      'Community support',
    ],
    cta: 'Get Started',
    recommended: false,
  },
  {
    name: 'Creator',
    price: 19,
    period: '/mo',
    videos: '30 videos / month',
    features: [
      '1080p output',
      'Word-level captions',
      '3 YouTube channels',
      'Priority queue',
      'Caption style customization',
    ],
    cta: 'Start Free Trial',
    recommended: false,
  },
  {
    name: 'Pro',
    price: 49,
    period: '/mo',
    videos: '100 videos / month',
    features: [
      '1080p output',
      'All caption styles',
      '10 YouTube channels',
      'Priority queue',
      'API access',
      'Custom voice cloning',
      'Bring your own keys',
    ],
    cta: 'Start Free Trial',
    recommended: true,
  },
  {
    name: 'Agency',
    price: 149,
    period: '/mo',
    videos: '500 videos / month',
    features: [
      'Everything in Pro',
      'Unlimited channels',
      'Team collaboration (10 seats)',
      'White-label option',
      'Dedicated support',
      'SLA guarantee',
    ],
    cta: 'Contact Sales',
    recommended: false,
  },
]

function CheckIcon() {
  return (
    <svg
      className="w-4 h-4 text-green-400 shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
}

export function PricingSection() {
  return (
    <section className="relative py-24 sm:py-32 px-6">
      <div className="max-w-6xl mx-auto">
        <FadeIn>
          <h2 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold text-center text-white tracking-tight">
            Simple{' '}
            <span className="bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
              pricing
            </span>
          </h2>
          <p className="mt-4 text-zinc-400 text-center text-lg max-w-2xl mx-auto">
            Start free. Scale as you grow. No hidden fees.
          </p>
        </FadeIn>

        <div className="mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map((plan, index) => (
            <FadeIn key={plan.name} delay={index * 100} direction="up">
              <div
                className="relative flex flex-col h-full"
                style={{ perspective: '1000px' }}
              >
                {/* Animated gradient border for recommended plan */}
                {plan.recommended && (
                  <div
                    className="absolute -inset-[1px] rounded-2xl z-0"
                    style={{
                      background:
                        'linear-gradient(135deg, #7c3aed, #2563eb, #06b6d4)',
                      backgroundSize: '200% 200%',
                      animation: 'borderShift 4s ease infinite',
                    }}
                  />
                )}

                <div
                  className={`relative z-10 flex flex-col h-full rounded-2xl border p-6 ${
                    plan.recommended
                      ? 'bg-[#18181b] border-transparent'
                      : 'bg-white/[0.03] border-white/[0.06]'
                  }`}
                >
                  {plan.recommended && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="inline-flex items-center rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 px-3 py-1 text-xs font-medium text-white">
                        Recommended
                      </span>
                    </div>
                  )}

                  <div className="mb-6">
                    <h3 className="font-display text-lg font-semibold text-white">
                      {plan.name}
                    </h3>
                    <div className="mt-3 flex items-baseline gap-1">
                      {plan.price === 0 ? (
                        <span className="text-4xl font-bold text-white font-display">
                          Free
                        </span>
                      ) : (
                        <>
                          <span className="text-4xl font-bold text-white font-display">
                            ${plan.price}
                          </span>
                          <span className="text-sm text-zinc-500">
                            {plan.period}
                          </span>
                        </>
                      )}
                    </div>
                    <p className="mt-2 text-sm text-zinc-400">{plan.videos}</p>
                  </div>

                  <ul className="mb-8 flex-1 space-y-3">
                    {plan.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-start gap-2 text-sm text-zinc-300"
                      >
                        <CheckIcon />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    variant={plan.recommended ? 'primary' : 'outline'}
                    className={`w-full ${
                      plan.recommended
                        ? 'shadow-lg shadow-violet-500/25'
                        : ''
                    }`}
                  >
                    {plan.cta}
                  </Button>
                </div>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  )
}
