'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button, Card, CardContent, CardHeader, CardTitle, cn } from '@repo/ui'

interface Plan {
  id: string
  name: string
  display_name: string
  price_cents: number
  videos_per_month: number
  channels_limit: number
  team_seats: number
  features: Record<string, boolean>
  overage_cents: number
}

const PLACEHOLDER_PLANS: Plan[] = [
  {
    id: '1',
    name: 'free',
    display_name: 'Free',
    price_cents: 0,
    videos_per_month: 3,
    channels_limit: 1,
    team_seats: 1,
    features: { caption_styles: false, byok: false, trending_topics: false },
    overage_cents: 0,
  },
  {
    id: '2',
    name: 'creator',
    display_name: 'Creator',
    price_cents: 1900,
    videos_per_month: 30,
    channels_limit: 3,
    team_seats: 1,
    features: { caption_styles: true, byok: true, trending_topics: true },
    overage_cents: 75,
  },
  {
    id: '3',
    name: 'pro',
    display_name: 'Pro',
    price_cents: 4900,
    videos_per_month: 100,
    channels_limit: 10,
    team_seats: 5,
    features: { caption_styles: true, byok: true, trending_topics: true },
    overage_cents: 60,
  },
  {
    id: '4',
    name: 'agency',
    display_name: 'Agency',
    price_cents: 14900,
    videos_per_month: 500,
    channels_limit: 50,
    team_seats: 25,
    features: { caption_styles: true, byok: true, trending_topics: true },
    overage_cents: 40,
  },
  {
    id: '5',
    name: 'enterprise',
    display_name: 'Enterprise',
    price_cents: -1,
    videos_per_month: -1,
    channels_limit: -1,
    team_seats: -1,
    features: { caption_styles: true, byok: true, trending_topics: true },
    overage_cents: 0,
  },
]

const CURRENT_PLAN = 'creator'

function FeatureRow({ label, included }: { label: string; included: boolean }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      <span className={included ? 'text-green-400' : 'text-zinc-400'}>
        {included ? '\u2713' : '\u2717'}
      </span>
      <span className={included ? 'text-zinc-300' : 'text-zinc-500'}>{label}</span>
    </li>
  )
}

export default function PlansPage() {
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null)

  async function handleSelectPlan(planName: string) {
    if (planName === 'enterprise') {
      window.location.href = 'mailto:sales@shortfactory.io?subject=Enterprise Plan'
      return
    }

    setLoadingPlan(planName)
    try {
      const res = await fetch('/api/v1/billing/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: planName }),
      })
      const data = await res.json()
      if (data.checkout_url) {
        window.location.href = data.checkout_url
      }
    } catch {
      // Handle error
    } finally {
      setLoadingPlan(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/dashboard/billing"
          className="mb-4 inline-flex items-center text-sm text-zinc-400 hover:text-zinc-200"
        >
          &larr; Back to Billing
        </Link>
        <h1 className="font-display text-3xl font-bold">Plans</h1>
        <p className="mt-1 text-zinc-400">
          Choose the plan that fits your needs.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {PLACEHOLDER_PLANS.map((plan) => {
          const isCurrent = plan.name === CURRENT_PLAN
          const isEnterprise = plan.name === 'enterprise'
          const isFree = plan.name === 'free'

          return (
            <Card
              key={plan.id}
              className={cn(
                'relative flex flex-col',
                isCurrent && 'ring-2 ring-violet-500/50',
              )}
            >
              {isCurrent && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-violet-500 px-3 py-0.5 text-xs font-medium text-white">
                  Current
                </div>
              )}
              <CardHeader>
                <CardTitle>{plan.display_name}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col space-y-4">
                <div>
                  {isEnterprise ? (
                    <p className="text-2xl font-bold text-zinc-100">Custom</p>
                  ) : (
                    <p className="text-2xl font-bold text-zinc-100">
                      ${(plan.price_cents / 100).toFixed(0)}
                      <span className="text-sm font-normal text-zinc-500">/mo</span>
                    </p>
                  )}
                </div>

                <ul className="flex-1 space-y-2">
                  <li className="text-sm text-zinc-300">
                    {plan.videos_per_month === -1
                      ? 'Unlimited videos'
                      : `${plan.videos_per_month} videos/mo`}
                  </li>
                  <li className="text-sm text-zinc-300">
                    {plan.channels_limit === -1
                      ? 'Unlimited channels'
                      : `${plan.channels_limit} channel${plan.channels_limit !== 1 ? 's' : ''}`}
                  </li>
                  <li className="text-sm text-zinc-300">
                    {plan.team_seats === -1
                      ? 'Unlimited team seats'
                      : `${plan.team_seats} team seat${plan.team_seats !== 1 ? 's' : ''}`}
                  </li>
                  <FeatureRow
                    label="Custom captions"
                    included={plan.features.caption_styles}
                  />
                  <FeatureRow
                    label="Bring your own keys"
                    included={plan.features.byok}
                  />
                  <FeatureRow
                    label="Trending topics"
                    included={plan.features.trending_topics}
                  />
                  {plan.overage_cents > 0 && (
                    <li className="text-xs text-zinc-500">
                      Overage: ${(plan.overage_cents / 100).toFixed(2)}/video
                    </li>
                  )}
                </ul>

                <Button
                  variant={isCurrent ? 'outline' : 'primary'}
                  className="w-full"
                  disabled={isCurrent || isFree || loadingPlan === plan.name}
                  onClick={() => handleSelectPlan(plan.name)}
                >
                  {isCurrent
                    ? 'Current Plan'
                    : isFree
                      ? 'Free'
                      : isEnterprise
                        ? 'Contact Sales'
                        : loadingPlan === plan.name
                          ? 'Loading...'
                          : 'Upgrade'}
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
