'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@repo/ui'

interface AdminStats {
  total_users: number
  total_jobs: number
  completed_jobs: number
  failed_jobs: number
  active_jobs: number
  total_cost: number
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/admin/stats`,
      { credentials: 'include' }
    )
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-zinc-400">Loading admin stats...</div>
  if (error) return <div className="p-8 text-red-400">Error: {error}</div>
  if (!stats) return null

  const cards = [
    { label: 'Total Users', value: stats.total_users },
    { label: 'Total Jobs', value: stats.total_jobs },
    { label: 'Completed', value: stats.completed_jobs },
    { label: 'Failed', value: stats.failed_jobs },
    { label: 'Active', value: stats.active_jobs },
    { label: 'Total Cost', value: `$${stats.total_cost.toFixed(2)}` },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold text-white">Admin Dashboard</h1>
        <p className="mt-1 text-zinc-400">System overview — live data from API.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <Card key={c.label}>
            <CardContent className="p-6">
              <p className="text-sm text-zinc-400">{c.label}</p>
              <p className="mt-1 text-2xl font-semibold text-zinc-50 font-display">
                {typeof c.value === 'number' ? c.value.toLocaleString() : c.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
