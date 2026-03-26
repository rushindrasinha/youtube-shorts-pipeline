'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button, Card, CardContent, CardHeader, CardTitle } from '@repo/ui'

interface Subscription {
  plan: {
    name: string
    display_name: string
    videos_per_month: number
    price_cents: number
  }
  status: string
  current_period_end: string | null
  cancel_at_period_end: boolean
}

interface Usage {
  videos_created: number
  videos_limit: number
  overage_count: number
  period_start: string
  period_end: string
}

// Placeholder data — will be replaced with API calls
const PLACEHOLDER_SUB: Subscription = {
  plan: {
    name: 'creator',
    display_name: 'Creator',
    videos_per_month: 30,
    price_cents: 1900,
  },
  status: 'active',
  current_period_end: '2026-04-25T00:00:00Z',
  cancel_at_period_end: false,
}

const PLACEHOLDER_USAGE: Usage = {
  videos_created: 12,
  videos_limit: 30,
  overage_count: 0,
  period_start: '2026-03-01',
  period_end: '2026-03-31',
}

function UsageBar({ used, limit }: { used: number; limit: number }) {
  const pct = limit > 0 ? Math.min((used / limit) * 100, 100) : 0
  const isHigh = pct >= 80
  const isOver = used > limit

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-zinc-400">
          {used} / {limit === -1 ? 'Unlimited' : limit} videos
        </span>
        {isOver && (
          <span className="text-amber-400 text-xs">
            {used - limit} overage
          </span>
        )}
      </div>
      <div className="h-2 w-full rounded-full bg-white/[0.06]">
        <div
          className={`h-full rounded-full transition-all ${
            isOver
              ? 'bg-amber-500'
              : isHigh
                ? 'bg-yellow-500'
                : 'bg-gradient-to-r from-violet-500 to-indigo-500'
          }`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  )
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function BillingPage() {
  const [loading, setLoading] = useState(false)
  const sub = PLACEHOLDER_SUB
  const usage = PLACEHOLDER_USAGE

  async function handleManageBilling() {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/billing/portal', { method: 'POST' })
      const data = await res.json()
      if (data.portal_url) {
        window.location.href = data.portal_url
      }
    } catch {
      // Handle error
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold">Billing</h1>
          <p className="mt-1 text-zinc-400">
            Manage your subscription and usage.
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleManageBilling} disabled={loading}>
            {loading ? 'Loading...' : 'Manage Billing'}
          </Button>
          <Button variant="primary" asChild>
            <Link href="/dashboard/billing/plans">Change Plan</Link>
          </Button>
        </div>
      </div>

      {/* Current Plan */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Current Plan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-baseline justify-between">
              <h3 className="text-2xl font-bold text-zinc-100">
                {sub.plan.display_name}
              </h3>
              <span className="text-lg text-zinc-400">
                ${(sub.plan.price_cents / 100).toFixed(2)}/mo
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  sub.status === 'active'
                    ? 'bg-green-500/10 text-green-400'
                    : sub.status === 'past_due'
                      ? 'bg-red-500/10 text-red-400'
                      : 'bg-zinc-500/10 text-zinc-400'
                }`}
              >
                {sub.status}
              </span>
              {sub.cancel_at_period_end && (
                <span className="text-xs text-amber-400">Cancels at period end</span>
              )}
            </div>
            {sub.current_period_end && (
              <p className="text-sm text-zinc-500">
                Next billing date: {formatDate(sub.current_period_end)}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Usage */}
        <Card>
          <CardHeader>
            <CardTitle>Usage This Period</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <UsageBar used={usage.videos_created} limit={usage.videos_limit} />
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-zinc-500">Period</p>
                <p className="text-zinc-300">
                  {formatDate(usage.period_start)} - {formatDate(usage.period_end)}
                </p>
              </div>
              <div>
                <p className="text-zinc-500">Overage</p>
                <p className="text-zinc-300">
                  {usage.overage_count} video{usage.overage_count !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Invoices */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Invoices</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-500">
            View and download invoices in the{' '}
            <button
              onClick={handleManageBilling}
              className="text-violet-400 hover:text-violet-300 underline"
            >
              Stripe Customer Portal
            </button>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
