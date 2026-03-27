'use client'

export default function DashboardError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <div className="text-center space-y-4">
        <h2 className="text-xl font-semibold text-zinc-50">Something went wrong</h2>
        <p className="text-zinc-400">{error.message}</p>
        <button onClick={reset} className="rounded-lg bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-500">
          Try again
        </button>
      </div>
    </div>
  )
}
