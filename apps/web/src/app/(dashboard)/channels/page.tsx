'use client'

import { useEffect, useState } from 'react'
import { Button, Card, CardContent, CardHeader, CardTitle, cn } from '@repo/ui'

interface Channel {
  id: string
  channel_id: string
  channel_title: string | null
  channel_thumbnail: string | null
  default_privacy: string
  auto_upload: boolean
  is_active: boolean
  last_upload_at: string | null
  team_id: string | null
}

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([])
  const [loading, setLoading] = useState(true)
  const [connecting, setConnecting] = useState(false)

  useEffect(() => {
    fetch('/api/v1/channels', { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => setChannels(data.items || []))
      .catch(() => setChannels([]))
      .finally(() => setLoading(false))
  }, [])

  const handleConnect = async () => {
    setConnecting(true)
    try {
      const res = await fetch('/api/v1/channels/connect', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (res.ok) {
        const data = await res.json()
        window.location.href = data.auth_url
      }
    } finally {
      setConnecting(false)
    }
  }

  const handleDisconnect = async (channelId: string) => {
    const res = await fetch(`/api/v1/channels/${channelId}`, {
      method: 'DELETE',
      credentials: 'include',
    })
    if (res.ok) {
      setChannels((prev) => prev.filter((c) => c.id !== channelId))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold">YouTube Channels</h1>
          <p className="mt-1 text-zinc-400">
            Connect your YouTube channels for automatic uploads.
          </p>
        </div>
        <Button
          variant="primary"
          onClick={handleConnect}
          disabled={connecting}
        >
          {connecting ? 'Connecting...' : 'Connect Channel'}
        </Button>
      </div>

      {loading ? (
        <p className="text-zinc-400">Loading channels...</p>
      ) : channels.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="mb-4 text-zinc-400">
              No channels connected yet. Connect your YouTube channel to enable
              auto-upload.
            </p>
            <Button variant="primary" onClick={handleConnect}>
              Connect YouTube Channel
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {channels.map((channel) => (
            <Card key={channel.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-4">
                  {channel.channel_thumbnail && (
                    <img
                      src={channel.channel_thumbnail}
                      alt={channel.channel_title || 'Channel'}
                      className="h-10 w-10 rounded-full"
                    />
                  )}
                  <div>
                    <p className="text-sm font-medium text-zinc-100">
                      {channel.channel_title || channel.channel_id}
                    </p>
                    <div className="mt-1 flex gap-3 text-xs text-zinc-500">
                      <span>Privacy: {channel.default_privacy}</span>
                      <span>
                        Auto-upload: {channel.auto_upload ? 'On' : 'Off'}
                      </span>
                      {channel.team_id && (
                        <span className="text-violet-400">Team channel</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                      channel.is_active
                        ? 'bg-green-500/10 text-green-400'
                        : 'bg-red-500/10 text-red-400',
                    )}
                  >
                    {channel.is_active ? 'Active' : 'Disconnected'}
                  </span>
                  <Button
                    variant="secondary"
                    onClick={() => handleDisconnect(channel.id)}
                  >
                    Disconnect
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
