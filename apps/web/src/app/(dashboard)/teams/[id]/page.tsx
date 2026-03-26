'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { Button, Card, CardContent, CardHeader, CardTitle, cn } from '@repo/ui'

interface TeamMember {
  id: string
  user_id: string
  email: string
  display_name: string | null
  role: string
  joined_at: string
}

interface TeamDetail {
  id: string
  name: string
  slug: string
  brand_color: string | null
  members_count: number
  channels_count: number
  max_members: number
}

const ROLE_COLORS: Record<string, string> = {
  owner: 'bg-amber-500/10 text-amber-400',
  admin: 'bg-violet-500/10 text-violet-400',
  member: 'bg-blue-500/10 text-blue-400',
  viewer: 'bg-zinc-500/10 text-zinc-400',
}

export default function TeamDetailPage() {
  const params = useParams()
  const teamId = params.id as string

  const [team, setTeam] = useState<TeamDetail | null>(null)
  const [members, setMembers] = useState<TeamMember[]>([])
  const [loading, setLoading] = useState(true)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [showInvite, setShowInvite] = useState(false)

  useEffect(() => {
    Promise.all([
      fetch(`/api/v1/teams/${teamId}`, { credentials: 'include' }).then((r) =>
        r.json(),
      ),
      fetch(`/api/v1/teams/${teamId}/members`, { credentials: 'include' }).then(
        (r) => r.json(),
      ),
    ])
      .then(([teamData, membersData]) => {
        setTeam(teamData)
        setMembers(membersData.items || [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [teamId])

  const handleInvite = async () => {
    const res = await fetch(`/api/v1/teams/${teamId}/members/invite`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
    })
    if (res.ok) {
      setShowInvite(false)
      setInviteEmail('')
    }
  }

  if (loading) {
    return <p className="text-zinc-400">Loading team...</p>
  }

  if (!team) {
    return <p className="text-zinc-400">Team not found.</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {team.brand_color && (
            <div
              className="h-6 w-6 rounded-full"
              style={{ backgroundColor: team.brand_color }}
            />
          )}
          <div>
            <h1 className="font-display text-3xl font-bold">{team.name}</h1>
            <p className="mt-1 text-zinc-400">
              {team.members_count} / {team.max_members} members
              {' | '}
              {team.channels_count} channels
            </p>
          </div>
        </div>
        <Button variant="primary" onClick={() => setShowInvite(true)}>
          Invite Member
        </Button>
      </div>

      {showInvite && (
        <Card>
          <CardContent className="space-y-4 p-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Email
              </label>
              <input
                type="email"
                className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-violet-500 focus:outline-none"
                placeholder="teammate@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Role
              </label>
              <select
                className="rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 focus:border-violet-500 focus:outline-none"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
              >
                <option value="admin">Admin</option>
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <div className="flex gap-2">
              <Button variant="primary" onClick={handleInvite} disabled={!inviteEmail.trim()}>
                Send Invite
              </Button>
              <Button variant="secondary" onClick={() => setShowInvite(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Members */}
      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-zinc-800">
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between py-3"
              >
                <div>
                  <p className="text-sm font-medium text-zinc-100">
                    {member.display_name || member.email}
                  </p>
                  <p className="text-xs text-zinc-500">{member.email}</p>
                </div>
                <span
                  className={cn(
                    'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
                    ROLE_COLORS[member.role] || ROLE_COLORS.viewer,
                  )}
                >
                  {member.role}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Activity placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-400">
            Team activity feed will appear here as members create videos and
            connect channels.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
