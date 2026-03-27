'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button, Card, CardContent, CardHeader, CardTitle, cn } from '@repo/ui'
import { StatusBadge } from '@/components/shared/status-badge'

type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'canceled'

interface Job {
  id: string
  topic: string
  status: JobStatus
  progress_pct: number
  current_stage: string | null
  created_at: string
  completed_at: string | null
  cost_usd: number
}

const PLACEHOLDER_JOBS: Job[] = [
  {
    id: '1',
    topic: 'SpaceX successfully lands Starship',
    status: 'running',
    progress_pct: 72,
    current_stage: 'captions',
    created_at: '2026-03-25T12:00:00Z',
    completed_at: null,
    cost_usd: 0.08,
  },
  {
    id: '2',
    topic: 'AI Advances in 2026',
    status: 'completed',
    progress_pct: 100,
    current_stage: null,
    created_at: '2026-03-24T10:30:00Z',
    completed_at: '2026-03-24T10:33:22Z',
    cost_usd: 0.11,
  },
  {
    id: '3',
    topic: 'Climate Summit Results',
    status: 'completed',
    progress_pct: 100,
    current_stage: null,
    created_at: '2026-03-23T14:00:00Z',
    completed_at: '2026-03-23T14:02:45Z',
    cost_usd: 0.10,
  },
  {
    id: '4',
    topic: 'New iPhone 18 Leaks Revealed',
    status: 'queued',
    progress_pct: 0,
    current_stage: null,
    created_at: '2026-03-25T13:00:00Z',
    completed_at: null,
    cost_usd: 0,
  },
  {
    id: '5',
    topic: 'Bitcoin Hits New All Time High',
    status: 'failed',
    progress_pct: 45,
    current_stage: null,
    created_at: '2026-03-22T09:00:00Z',
    completed_at: null,
    cost_usd: 0.05,
  },
]

const FILTER_TABS: { label: string; value: JobStatus | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Queued', value: 'queued' },
  { label: 'Running', value: 'running' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
]

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function JobsPage() {
  const [filter, setFilter] = useState<JobStatus | 'all'>('all')

  const filteredJobs =
    filter === 'all'
      ? PLACEHOLDER_JOBS
      : PLACEHOLDER_JOBS.filter((j) => j.status === filter)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold">Jobs</h1>
          <p className="mt-1 text-zinc-400">
            Track your video generation pipeline.
          </p>
        </div>
        <Button variant="primary" asChild>
          <Link href="/dashboard/jobs/new">New Video</Link>
        </Button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 rounded-lg bg-white/[0.03] p-1">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
              filter === tab.value
                ? 'bg-white/[0.06] text-zinc-50'
                : 'text-zinc-400 hover:text-zinc-200',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Job list */}
      <div className="space-y-3">
        {filteredJobs.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-zinc-400">No jobs found.</p>
            </CardContent>
          </Card>
        ) : (
          filteredJobs.map((job) => (
            <Link key={job.id} href={`/dashboard/jobs/${job.id}`}>
              <Card className="transition-colors hover:bg-white/[0.04]">
                <CardContent className="flex items-center justify-between p-4">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-zinc-100">
                      {job.topic}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {formatDate(job.created_at)}
                      {job.cost_usd > 0 && ` · $${job.cost_usd.toFixed(2)}`}
                    </p>
                  </div>
                  <div className="ml-4 flex items-center gap-4">
                    {(job.status === 'running' || (job.status === 'failed' && job.progress_pct > 0)) && (
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-28 rounded-full bg-white/[0.06]">
                          <div
                            className={cn(
                              'h-full rounded-full transition-all',
                              job.status === 'failed'
                                ? 'bg-red-500'
                                : 'bg-gradient-to-r from-violet-500 to-indigo-500',
                            )}
                            style={{ width: `${job.progress_pct}%` }}
                          />
                        </div>
                        <span className="text-xs text-zinc-400">
                          {job.progress_pct}%
                        </span>
                      </div>
                    )}
                    <StatusBadge status={job.status} />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))
        )}
      </div>
    </div>
  )
}
