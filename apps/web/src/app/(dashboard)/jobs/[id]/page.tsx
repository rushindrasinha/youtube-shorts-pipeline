'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Button, Card, CardContent, CardHeader, CardTitle, cn } from '@repo/ui'
import { useJobProgress } from '@/hooks/use-job-progress'
import { JobStages } from '@/components/jobs/job-stages'
import type { JobDetailResponse } from '@/types/api'

// Placeholder job detail for demonstration
const PLACEHOLDER_JOB: JobDetailResponse = {
  id: '1',
  topic: 'SpaceX successfully lands Starship',
  status: 'running',
  progress_pct: 65,
  current_stage: 'captions',
  created_at: '2026-03-25T12:00:00Z',
  completed_at: null,
  cost_usd: 0.08,
  error_message: null,
  stages: [
    { name: 'research', status: 'done', duration_ms: 2100 },
    { name: 'draft', status: 'done', duration_ms: 3500 },
    { name: 'broll', status: 'done', duration_ms: 12000 },
    { name: 'voiceover', status: 'done', duration_ms: 8200 },
    { name: 'captions', status: 'running', duration_ms: null },
    { name: 'music', status: 'pending', duration_ms: null },
    { name: 'assemble', status: 'pending', duration_ms: null },
    { name: 'thumbnail', status: 'pending', duration_ms: null },
  ],
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    queued: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    running: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
    completed: 'bg-green-500/10 text-green-400 border-green-500/20',
    failed: 'bg-red-500/10 text-red-400 border-red-500/20',
    canceled: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium capitalize',
        styles[status] || styles.canceled,
      )}
    >
      {status === 'running' ? 'Generating...' : status}
    </span>
  )
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function JobDetailPage() {
  const params = useParams()
  const jobId = params.id as string

  // In a real implementation, we would fetch the job data using api.jobs.get(jobId)
  // and use the SSE hook for live progress updates.
  const { progress, connected } = useJobProgress(
    PLACEHOLDER_JOB.status === 'running' ? jobId : null,
  )

  // Use SSE progress if available, otherwise fall back to placeholder
  const currentProgress = progress?.progress_pct ?? PLACEHOLDER_JOB.progress_pct
  const currentStage = progress?.stage ?? PLACEHOLDER_JOB.current_stage
  const job = PLACEHOLDER_JOB

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Back link */}
      <Link
        href="/dashboard/jobs"
        className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
      >
        &larr; Back to Jobs
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-2xl font-bold">{job.topic}</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Created {formatDate(job.created_at)}
            {job.cost_usd > 0 && ` · Cost: $${job.cost_usd.toFixed(2)}`}
          </p>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {/* Progress bar */}
      {(job.status === 'running' || job.status === 'queued') && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-zinc-300">Progress</p>
              <p className="text-sm text-zinc-400">{currentProgress}%</p>
            </div>
            <div className="h-2 w-full rounded-full bg-white/[0.06] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-500"
                style={{ width: `${currentProgress}%` }}
              />
            </div>
            {connected && (
              <p className="mt-2 text-xs text-green-400">
                Live updates connected
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Error message */}
      {job.status === 'failed' && job.error_message && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3">
          <p className="text-sm font-medium text-red-400">Error</p>
          <p className="mt-1 text-sm text-red-300">{job.error_message}</p>
        </div>
      )}

      {/* Pipeline stages */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Stages</CardTitle>
        </CardHeader>
        <CardContent>
          <JobStages stages={job.stages} currentStage={currentStage} />
        </CardContent>
      </Card>

      {/* Completed state */}
      {job.status === 'completed' && (
        <Card>
          <CardHeader>
            <CardTitle>Video Ready</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-zinc-400">
              Your video has been generated successfully.
            </p>
            <div className="flex gap-3">
              <Button variant="primary">Download Video</Button>
              <Button variant="outline">Upload to YouTube</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Job metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-zinc-500">Job ID</dt>
              <dd className="mt-0.5 font-mono text-xs text-zinc-300">
                {jobId}
              </dd>
            </div>
            <div>
              <dt className="text-zinc-500">Status</dt>
              <dd className="mt-0.5 capitalize text-zinc-300">{job.status}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Created</dt>
              <dd className="mt-0.5 text-zinc-300">
                {formatDate(job.created_at)}
              </dd>
            </div>
            <div>
              <dt className="text-zinc-500">Completed</dt>
              <dd className="mt-0.5 text-zinc-300">
                {job.completed_at ? formatDate(job.completed_at) : '---'}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  )
}
