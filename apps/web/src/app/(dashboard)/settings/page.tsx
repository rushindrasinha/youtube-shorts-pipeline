'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button, Card, CardContent, CardHeader, CardTitle } from '@repo/ui'

export default function SettingsPage() {
  const [displayName, setDisplayName] = useState('')
  const [defaultLanguage, setDefaultLanguage] = useState('en')
  const [captionStyle, setCaptionStyle] = useState('default')
  const [musicGenre, setMusicGenre] = useState('none')
  const [saving, setSaving] = useState(false)

  async function handleSave() {
    setSaving(true)
    try {
      // TODO: call API to save preferences
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Settings</h1>
        <p className="mt-1 text-zinc-400">
          Manage your account preferences.
        </p>
      </div>

      {/* User Preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">
              Display Name
            </label>
            <input
              type="text"
              className="w-full rounded-md border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-violet-500/50 focus:outline-none"
              placeholder="Your display name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">
              Default Language
            </label>
            <select
              className="w-full rounded-md border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-sm text-zinc-100 focus:border-violet-500/50 focus:outline-none"
              value={defaultLanguage}
              onChange={(e) => setDefaultLanguage(e.target.value)}
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="pt">Portuguese</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">
              Caption Style
            </label>
            <select
              className="w-full rounded-md border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-sm text-zinc-100 focus:border-violet-500/50 focus:outline-none"
              value={captionStyle}
              onChange={(e) => setCaptionStyle(e.target.value)}
            >
              <option value="default">Default</option>
              <option value="bold">Bold</option>
              <option value="minimal">Minimal</option>
              <option value="neon">Neon</option>
              <option value="typewriter">Typewriter</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">
              Music Genre
            </label>
            <select
              className="w-full rounded-md border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-sm text-zinc-100 focus:border-violet-500/50 focus:outline-none"
              value={musicGenre}
              onChange={(e) => setMusicGenre(e.target.value)}
            >
              <option value="none">None</option>
              <option value="lofi">Lo-fi</option>
              <option value="cinematic">Cinematic</option>
              <option value="upbeat">Upbeat</option>
              <option value="electronic">Electronic</option>
              <option value="ambient">Ambient</option>
            </select>
          </div>

          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Preferences'}
          </Button>
        </CardContent>
      </Card>

      {/* Links to sub-pages */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Link href="/dashboard/settings/provider-keys">
          <Card className="transition-colors hover:bg-white/[0.04]">
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-zinc-100">Provider Keys</h3>
              <p className="mt-1 text-sm text-zinc-400">
                Bring your own API keys for AI providers.
              </p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/dashboard/settings/api-keys">
          <Card className="transition-colors hover:bg-white/[0.04]">
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-zinc-100">API Keys</h3>
              <p className="mt-1 text-sm text-zinc-400">
                Manage API keys for programmatic access.
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  )
}
