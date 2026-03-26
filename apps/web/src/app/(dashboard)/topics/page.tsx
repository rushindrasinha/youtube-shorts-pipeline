'use client'

import { useEffect, useState } from 'react'
import { Button, Card, CardContent, CardHeader, CardTitle, cn } from '@repo/ui'

interface TrendingTopic {
  title: string
  source: string
  trending_score: number
  summary: string | null
  url: string | null
  metadata: Record<string, unknown>
}

function formatScore(score: number): string {
  return (score * 100).toFixed(0)
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return 'text-green-400'
  if (score >= 0.5) return 'text-yellow-400'
  return 'text-zinc-400'
}

export default function TopicsPage() {
  const [topics, setTopics] = useState<TrendingTopic[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/v1/topics/trending', { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => setTopics(data.items || []))
      .catch(() => setTopics([]))
      .finally(() => setLoading(false))
  }, [])

  const handleQuickCreate = async (title: string) => {
    setCreating(title)
    try {
      const res = await fetch('/api/v1/topics/quick-create', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic_title: title }),
      })
      if (res.ok) {
        const job = await res.json()
        window.location.href = `/dashboard/jobs/${job.id}`
      }
    } finally {
      setCreating(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Trending Topics</h1>
        <p className="mt-1 text-zinc-400">
          Discover what is trending and create videos with one click.
        </p>
      </div>

      {loading ? (
        <p className="text-zinc-400">Loading trending topics...</p>
      ) : topics.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-zinc-400">
              No trending topics available right now. Check back in a few
              minutes.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {topics.map((topic) => (
            <Card key={topic.title} className="transition-colors hover:bg-white/[0.04]">
              <CardContent className="flex items-center justify-between p-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3">
                    <p className="truncate text-sm font-medium text-zinc-100">
                      {topic.title}
                    </p>
                    <span
                      className={cn(
                        'shrink-0 text-xs font-semibold',
                        getScoreColor(topic.trending_score),
                      )}
                    >
                      {formatScore(topic.trending_score)}%
                    </span>
                  </div>
                  <div className="mt-1 flex gap-3 text-xs text-zinc-500">
                    <span>{topic.source}</span>
                    {topic.summary && (
                      <span className="truncate">{topic.summary}</span>
                    )}
                  </div>
                </div>
                <div className="ml-4 flex items-center gap-2">
                  {topic.url && (
                    <a
                      href={topic.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-zinc-400 underline hover:text-zinc-200"
                    >
                      Source
                    </a>
                  )}
                  <Button
                    variant="primary"
                    onClick={() => handleQuickCreate(topic.title)}
                    disabled={creating === topic.title}
                  >
                    {creating === topic.title ? 'Creating...' : 'Create Video'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
