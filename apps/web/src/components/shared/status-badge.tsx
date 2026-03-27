import { cn } from '@repo/ui'

const statusStyles: Record<string, string> = {
  completed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  running: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  queued: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  canceled: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
      statusStyles[status] || statusStyles.canceled
    )}>
      {status}
    </span>
  )
}
