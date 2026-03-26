'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button, Card, CardContent, CardHeader, CardTitle, cn } from '@repo/ui'

interface ProviderKey {
  provider: string
  is_active: boolean
  last_verified_at: string | null
  key_prefix: string
}

const PROVIDERS = [
  {
    id: 'anthropic',
    name: 'Anthropic',
    description: 'Claude AI models for script writing and research.',
    placeholder: 'sk-ant-...',
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    description: 'Gemini models for content generation.',
    placeholder: 'AI...',
  },
  {
    id: 'elevenlabs',
    name: 'ElevenLabs',
    description: 'Text-to-speech for voiceover generation.',
    placeholder: 'xi-...',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    description: 'GPT models for additional AI capabilities.',
    placeholder: 'sk-...',
  },
]

// Placeholder connected keys
const PLACEHOLDER_KEYS: ProviderKey[] = [
  {
    provider: 'anthropic',
    is_active: true,
    last_verified_at: '2026-03-25T12:00:00Z',
    key_prefix: 'sk-ant-**',
  },
]

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function ProviderKeysPage() {
  const [connectedKeys, setConnectedKeys] = useState<ProviderKey[]>(PLACEHOLDER_KEYS)
  const [editingProvider, setEditingProvider] = useState<string | null>(null)
  const [keyInput, setKeyInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [verifying, setVerifying] = useState<string | null>(null)

  function getConnectedKey(providerId: string): ProviderKey | undefined {
    return connectedKeys.find((k) => k.provider === providerId)
  }

  async function handleSaveKey(providerId: string) {
    if (!keyInput.trim()) return
    setSaving(true)
    try {
      const res = await fetch(`/api/v1/users/me/provider-keys/${providerId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: keyInput }),
      })
      if (res.ok) {
        const data = await res.json()
        setConnectedKeys((prev) => {
          const filtered = prev.filter((k) => k.provider !== providerId)
          return [...filtered, data]
        })
        setEditingProvider(null)
        setKeyInput('')
      }
    } catch {
      // Handle error
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteKey(providerId: string) {
    try {
      const res = await fetch(`/api/v1/users/me/provider-keys/${providerId}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        setConnectedKeys((prev) => prev.filter((k) => k.provider !== providerId))
      }
    } catch {
      // Handle error
    }
  }

  async function handleVerifyKey(providerId: string) {
    setVerifying(providerId)
    try {
      const res = await fetch(
        `/api/v1/users/me/provider-keys/${providerId}/verify`,
        { method: 'POST' },
      )
      if (res.ok) {
        const data = await res.json()
        if (data.valid) {
          // Refresh the key list
          setConnectedKeys((prev) =>
            prev.map((k) =>
              k.provider === providerId
                ? { ...k, is_active: true, last_verified_at: new Date().toISOString() }
                : k,
            ),
          )
        }
      }
    } catch {
      // Handle error
    } finally {
      setVerifying(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/dashboard/settings"
          className="mb-4 inline-flex items-center text-sm text-zinc-400 hover:text-zinc-200"
        >
          &larr; Back to Settings
        </Link>
        <h1 className="font-display text-3xl font-bold">Provider API Keys</h1>
        <p className="mt-1 text-zinc-400">
          Bring your own API keys to use your own quotas and reduce costs.
          Keys are encrypted at rest.
        </p>
      </div>

      <div className="space-y-4">
        {PROVIDERS.map((provider) => {
          const connected = getConnectedKey(provider.id)
          const isEditing = editingProvider === provider.id

          return (
            <Card key={provider.id}>
              <CardContent className="flex items-start justify-between p-6">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold text-zinc-100">
                      {provider.name}
                    </h3>
                    {connected && (
                      <span
                        className={cn(
                          'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                          connected.is_active
                            ? 'bg-green-500/10 text-green-400'
                            : 'bg-red-500/10 text-red-400',
                        )}
                      >
                        {connected.is_active ? 'Connected' : 'Invalid'}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-zinc-500">{provider.description}</p>

                  {connected && !isEditing && (
                    <div className="mt-2 text-sm text-zinc-400">
                      <span className="font-mono">{connected.key_prefix}</span>
                      {connected.last_verified_at && (
                        <span className="ml-3 text-zinc-600">
                          Verified {formatDate(connected.last_verified_at)}
                        </span>
                      )}
                    </div>
                  )}

                  {isEditing && (
                    <div className="mt-3 flex gap-2">
                      <input
                        type="password"
                        value={keyInput}
                        onChange={(e) => setKeyInput(e.target.value)}
                        placeholder={provider.placeholder}
                        className="flex-1 rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-violet-500/50 focus:outline-none"
                      />
                      <Button
                        variant="primary"
                        onClick={() => handleSaveKey(provider.id)}
                        disabled={saving || !keyInput.trim()}
                      >
                        {saving ? 'Saving...' : 'Save'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setEditingProvider(null)
                          setKeyInput('')
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>

                {!isEditing && (
                  <div className="ml-4 flex gap-2">
                    {connected && (
                      <>
                        <Button
                          variant="outline"
                          onClick={() => handleVerifyKey(provider.id)}
                          disabled={verifying === provider.id}
                        >
                          {verifying === provider.id ? 'Verifying...' : 'Verify'}
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => handleDeleteKey(provider.id)}
                        >
                          Remove
                        </Button>
                      </>
                    )}
                    <Button
                      variant={connected ? 'outline' : 'primary'}
                      onClick={() => {
                        setEditingProvider(provider.id)
                        setKeyInput('')
                      }}
                    >
                      {connected ? 'Update' : 'Add Key'}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
