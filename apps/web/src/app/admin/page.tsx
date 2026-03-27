import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@repo/ui'
import { StatusBadge } from '@/components/shared/status-badge'

const systemStats = [
  { label: 'Total Users', value: '—', description: 'Registered accounts' },
  { label: 'Total Jobs', value: '—', description: 'All-time pipeline runs' },
  { label: 'Active Jobs', value: '—', description: 'Currently processing' },
  { label: 'Revenue (MRR)', value: '—', description: 'Monthly recurring' },
]

const recentJobs = [
  {
    id: '1',
    user: 'john@example.com',
    topic: 'SpaceX Starship Landing',
    status: 'completed',
    cost: '$0.12',
    created: '2 min ago',
  },
  {
    id: '2',
    user: 'jane@example.com',
    topic: 'AI Regulation EU 2026',
    status: 'running',
    cost: '$0.08',
    created: '5 min ago',
  },
  {
    id: '3',
    user: 'bob@example.com',
    topic: 'Climate Summit Results',
    status: 'failed',
    cost: '$0.03',
    created: '12 min ago',
  },
]

export default function AdminDashboard() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold text-white">
          Admin Dashboard
        </h1>
        <p className="mt-1 text-zinc-400">
          System overview and management.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {systemStats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-6">
              <p className="text-sm text-zinc-400">{stat.label}</p>
              <p className="mt-1 text-2xl font-semibold text-zinc-50 font-display">
                {stat.value}
              </p>
              <p className="mt-1 text-xs text-zinc-400">{stat.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent jobs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Jobs (System-wide)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="py-3 pr-4 text-left font-medium text-zinc-400">
                    User
                  </th>
                  <th className="py-3 pr-4 text-left font-medium text-zinc-400">
                    Topic
                  </th>
                  <th className="py-3 pr-4 text-left font-medium text-zinc-400">
                    Status
                  </th>
                  <th className="py-3 pr-4 text-left font-medium text-zinc-400">
                    Cost
                  </th>
                  <th className="py-3 text-left font-medium text-zinc-400">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {recentJobs.map((job) => (
                  <tr key={job.id} className="hover:bg-white/[0.02]">
                    <td className="py-3 pr-4 text-zinc-300 font-mono text-xs">
                      {job.user}
                    </td>
                    <td className="py-3 pr-4 text-zinc-200">{job.topic}</td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="py-3 pr-4 text-zinc-400 font-mono">
                      {job.cost}
                    </td>
                    <td className="py-3 text-zinc-500">{job.created}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
