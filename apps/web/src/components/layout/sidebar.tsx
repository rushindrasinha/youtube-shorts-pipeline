'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@repo/ui'

const navItems = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Jobs', href: '/dashboard/jobs' },
  { label: 'Videos', href: '/dashboard/videos' },
  { label: 'Trending', href: '/dashboard/topics' },
  { label: 'Channels', href: '/dashboard/channels' },
  { label: 'Teams', href: '/dashboard/teams' },
  { label: 'Settings', href: '/dashboard/settings' },
  { label: 'Billing', href: '/dashboard/billing' },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 shrink-0 border-r border-white/[0.06] bg-zinc-950 p-4">
      <Link href="/" className="font-display text-xl font-bold mb-8 block">
        Short
        <span className="text-violet-500">Factory</span>
      </Link>
      <nav className="space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'block rounded-lg px-3 py-2 text-sm transition-colors',
              pathname === item.href ||
                pathname?.startsWith(item.href + '/')
                ? 'bg-white/[0.06] text-zinc-50'
                : 'text-zinc-400 hover:text-zinc-50 hover:bg-white/[0.03]',
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}
