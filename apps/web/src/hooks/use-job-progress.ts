'use client'

import { useEffect, useState } from 'react'

interface ProgressEvent {
  type: string
  stage: string
  progress_pct: number
}

export function useJobProgress(jobId: string | null) {
  const [progress, setProgress] = useState<ProgressEvent | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    if (!jobId) return

    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/jobs/${jobId}/events`
    const source = new EventSource(url, { withCredentials: true })

    source.onopen = () => setConnected(true)

    source.addEventListener('stage_started', (e) => {
      setProgress(JSON.parse(e.data))
    })
    source.addEventListener('stage_completed', (e) => {
      setProgress(JSON.parse(e.data))
    })
    source.addEventListener('job_completed', (e) => {
      setProgress(JSON.parse(e.data))
      source.close()
    })
    source.addEventListener('job_failed', (e) => {
      setProgress(JSON.parse(e.data))
      source.close()
    })
    source.onerror = () => setConnected(false)

    return () => source.close()
  }, [jobId])

  return { progress, connected }
}
