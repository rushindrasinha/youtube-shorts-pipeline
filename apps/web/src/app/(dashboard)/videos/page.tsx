'use client'

import { useEffect, useState } from 'react'
import { Button, Card, CardContent } from '@repo/ui'
import { api } from '@/lib/api'

interface Video {
  id: string
  title: string
  thumbnail_url: string | null
  duration_seconds: number
  created_at: string
  youtube_status: string | null
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function VideosPage() {
  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.videos
      .list()
      .then((data) => setVideos((data.items as Video[]) || []))
      .catch(() => setVideos([]))
      .finally(() => setLoading(false))
  }, [])

  async function handleDelete(id: string) {
    try {
      await api.videos.delete(id)
      setVideos((prev) => prev.filter((v) => v.id !== id))
    } catch {
      // Handle error
    }
  }

  async function handleDownload(id: string) {
    try {
      const data = await api.videos.download(id)
      if (data.url) {
        window.open(data.url, '_blank')
      }
    } catch {
      // Handle error
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Videos</h1>
        <p className="mt-1 text-zinc-400">
          Your generated video library.
        </p>
      </div>

      {loading ? (
        <p className="text-zinc-400">Loading videos...</p>
      ) : videos.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="mb-2 text-zinc-400">
              No videos yet. Create your first video from a trending topic or new job.
            </p>
            <Button variant="primary" asChild>
              <a href="/dashboard/jobs/new">Create Video</a>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {videos.map((video) => (
            <Card key={video.id} className="overflow-hidden">
              <div className="relative aspect-[9/16] bg-zinc-800">
                {video.thumbnail_url ? (
                  <img
                    src={video.thumbnail_url}
                    alt={video.title}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-zinc-600">
                    No thumbnail
                  </div>
                )}
                <span className="absolute bottom-2 right-2 rounded bg-black/70 px-1.5 py-0.5 text-xs text-white">
                  {formatDuration(video.duration_seconds)}
                </span>
              </div>
              <CardContent className="space-y-3 p-4">
                <div>
                  <p className="truncate text-sm font-medium text-zinc-100">
                    {video.title}
                  </p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-zinc-400">
                    <span>{formatDate(video.created_at)}</span>
                    {video.youtube_status && (
                      <span className="rounded bg-white/[0.06] px-1.5 py-0.5">
                        YT: {video.youtube_status}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="flex-1 text-xs"
                    onClick={() => handleDownload(video.id)}
                  >
                    Download
                  </Button>
                  <Button
                    variant="outline"
                    className="flex-1 text-xs"
                    onClick={() => handleDelete(video.id)}
                  >
                    Delete
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
