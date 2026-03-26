import { cn } from '@repo/ui'
import type { StageInfo } from '@/types/api'

const STAGES = [
  'research',
  'draft',
  'broll',
  'voiceover',
  'captions',
  'music',
  'assemble',
  'thumbnail',
]

function StageIcon({ status }: { status: string }) {
  if (status === 'done') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-500/20 text-green-400 text-xs">
        &#10003;
      </span>
    )
  }
  if (status === 'running') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-violet-500/20 text-violet-400">
        <span className="h-2 w-2 rounded-full bg-violet-400 animate-pulse" />
      </span>
    )
  }
  if (status === 'failed') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500/20 text-red-400 text-xs">
        &#10005;
      </span>
    )
  }
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/[0.06] text-zinc-500">
      <span className="h-2 w-2 rounded-full bg-zinc-600" />
    </span>
  )
}

function formatDuration(ms: number | null): string {
  if (ms == null) return ''
  return `${(ms / 1000).toFixed(1)}s`
}

export function JobStages({
  stages,
  currentStage,
}: {
  stages: StageInfo[]
  currentStage: string | null
}) {
  const stageMap = new Map(stages.map((s) => [s.name, s]))

  return (
    <div className="space-y-2">
      {STAGES.map((name) => {
        const stage = stageMap.get(name)
        const status = stage?.status ?? 'pending'
        const isActive = name === currentStage

        return (
          <div
            key={name}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm',
              isActive && 'bg-white/[0.03]',
            )}
          >
            <StageIcon status={status} />
            <span
              className={cn(
                'capitalize',
                status === 'done'
                  ? 'text-zinc-300'
                  : status === 'running'
                    ? 'text-zinc-50 font-medium'
                    : 'text-zinc-500',
              )}
            >
              {name}
            </span>
            {status === 'running' && (
              <span className="ml-auto text-xs text-zinc-500">
                running...
              </span>
            )}
            {status === 'done' && stage?.duration_ms != null && (
              <span className="ml-auto text-xs text-zinc-500">
                {formatDuration(stage.duration_ms)}
              </span>
            )}
            {status === 'failed' && (
              <span className="ml-auto text-xs text-red-400">failed</span>
            )}
          </div>
        )
      })}
    </div>
  )
}
