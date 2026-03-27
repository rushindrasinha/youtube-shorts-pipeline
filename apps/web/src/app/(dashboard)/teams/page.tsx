'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Button, Card, CardContent, CardHeader, CardTitle, cn } from '@repo/ui'
import { api } from '@/lib/api'

interface Team {
  id: string
  name: string
  slug: string
  brand_color: string | null
  members_count: number
  channels_count: number
  created_at: string
}

export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState('#6366F1')

  useEffect(() => {
    api.teams
      .list()
      .then((data) => setTeams(data.items || []))
      .catch(() => setTeams([]))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async () => {
    try {
      const team = await api.teams.create({ name: newName })
      setTeams((prev) => [...prev, team as Team])
      setShowCreate(false)
      setNewName('')
    } catch {
      // Handle error
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold">Teams</h1>
          <p className="mt-1 text-zinc-400">
            Manage your teams and collaborate with others.
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowCreate(true)}>
          Create Team
        </Button>
      </div>

      {showCreate && (
        <Card>
          <CardContent className="space-y-4 p-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Team Name
              </label>
              <input
                type="text"
                className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-violet-500 focus:outline-none"
                placeholder="My Agency"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Brand Color
              </label>
              <input
                type="color"
                className="h-10 w-16 cursor-pointer rounded border border-zinc-700 bg-zinc-800"
                value={newColor}
                onChange={(e) => setNewColor(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button variant="primary" onClick={handleCreate} disabled={!newName.trim()}>
                Create
              </Button>
              <Button variant="secondary" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <p className="text-zinc-400">Loading teams...</p>
      ) : teams.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-zinc-400">
              No teams yet. Create one to start collaborating.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((team) => (
            <Link key={team.id} href={`/dashboard/teams/${team.id}`}>
              <Card className="transition-colors hover:bg-white/[0.04]">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    {team.brand_color && (
                      <div
                        className="h-4 w-4 rounded-full"
                        style={{ backgroundColor: team.brand_color }}
                      />
                    )}
                    <CardTitle className="text-lg">{team.name}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-6 text-sm text-zinc-400">
                    <span>{team.members_count} members</span>
                    <span>{team.channels_count} channels</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
