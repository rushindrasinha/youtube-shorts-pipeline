import Link from 'next/link'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@repo/ui'
import { StatusBadge } from '@/components/shared/status-badge'

const stats = [
  { label: 'Videos this month', value: '12 / 30' },
  { label: 'Active jobs', value: '3' },
  { label: 'Avg cost', value: '$0.11' },
]

const recentJobs = [
  {
    id: '1',
    topic: 'SpaceX successfully lands Starship',
    status: 'running' as const,
    progress_pct: 72,
  },
  {
    id: '2',
    topic: 'AI Advances in 2026',
    status: 'completed' as const,
    progress_pct: 100,
  },
  {
    id: '3',
    topic: 'Climate Summit Results',
    status: 'completed' as const,
    progress_pct: 100,
  },
]

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold">
          Good morning!
        </h1>
        <p className="mt-1 text-zinc-400">
          Here&apos;s what&apos;s happening with your videos.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-6">
              <p className="text-sm text-zinc-400">{stat.label}</p>
              <p className="mt-1 text-2xl font-semibold text-zinc-50">
                {stat.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Jobs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Jobs</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {recentJobs.map((job) => (
            <Link
              key={job.id}
              href={`/dashboard/jobs/${job.id}`}
              className="flex items-center justify-between rounded-lg px-3 py-3 transition-colors hover:bg-white/[0.03]"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-zinc-200">
                  {job.topic}
                </p>
              </div>
              <div className="ml-4 flex items-center gap-3">
                {job.status === 'running' && (
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-24 rounded-full bg-white/[0.06]">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500"
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
            </Link>
          ))}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="flex gap-4">
        <Button variant="primary" asChild>
          <Link href="/dashboard/jobs/new">New Video</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/dashboard/topics">Browse Trending</Link>
        </Button>
      </div>
    </div>
  )
}
