import Link from 'next/link'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen">
      {/* Admin header */}
      <header className="border-b border-white/[0.06] bg-[#09090b]">
        <div className="flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-6">
            <Link href="/" className="font-display text-lg font-bold text-white">
              Short
              <span className="bg-gradient-to-r from-violet-500 to-indigo-500 bg-clip-text text-transparent">
                Factory
              </span>
            </Link>
            <span className="rounded-full bg-red-500/10 px-2.5 py-0.5 text-xs font-medium text-red-400">
              Admin
            </span>
          </div>
          <nav className="flex items-center gap-4 text-sm">
            <Link
              href="/admin"
              className="text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/admin/users"
              className="text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Users
            </Link>
            <Link
              href="/admin/jobs"
              className="text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Jobs
            </Link>
          </nav>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
    </div>
  )
}
