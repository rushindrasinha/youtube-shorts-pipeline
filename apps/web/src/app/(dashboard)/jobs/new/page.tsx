'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@repo/ui'
import { api, ApiError } from '@/lib/api'

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi' },
]

export default function NewJobPage() {
  const router = useRouter()
  const [topic, setTopic] = useState('')
  const [context, setContext] = useState('')
  const [language, setLanguage] = useState('en')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const topicLength = topic.length
  const isTopicValid = topicLength >= 3 && topicLength <= 500

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!isTopicValid) return

    setError(null)
    setLoading(true)

    try {
      const job = await api.jobs.create({
        topic,
        context: context || undefined,
        language,
      })
      router.push(`/dashboard/jobs/${job.id}`)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('An unexpected error occurred')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <Link
          href="/dashboard/jobs"
          className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          &larr; Back to Jobs
        </Link>
        <h1 className="mt-4 font-display text-3xl font-bold">
          Create New Video
        </h1>
        <p className="mt-1 text-zinc-400">
          Enter a topic and we will generate a YouTube Short for you.
        </p>
      </div>

      <Card>
        <form onSubmit={handleSubmit}>
          <CardHeader>
            <CardTitle>Video Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {error && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Topic */}
            <div className="space-y-2">
              <label
                htmlFor="topic"
                className="text-sm font-medium text-zinc-300"
              >
                Topic <span className="text-red-400">*</span>
              </label>
              <textarea
                id="topic"
                required
                minLength={3}
                maxLength={500}
                rows={3}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                className="w-full rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-sm text-zinc-50 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 resize-none"
                placeholder="SpaceX successfully lands Starship on first attempt"
              />
              <p className="text-xs text-zinc-500">
                {topicLength}/500 characters
                {topicLength > 0 && topicLength < 3 && (
                  <span className="text-yellow-400"> (minimum 3)</span>
                )}
              </p>
            </div>

            {/* Context */}
            <div className="space-y-2">
              <label
                htmlFor="context"
                className="text-sm font-medium text-zinc-300"
              >
                Channel Context{' '}
                <span className="text-zinc-500">(optional)</span>
              </label>
              <textarea
                id="context"
                rows={2}
                value={context}
                onChange={(e) => setContext(e.target.value)}
                className="w-full rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-sm text-zinc-50 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 resize-none"
                placeholder="Tech news channel, energetic style, target audience: 18-35"
              />
            </div>

            {/* Language */}
            <div className="space-y-2">
              <label
                htmlFor="language"
                className="text-sm font-medium text-zinc-300"
              >
                Language
              </label>
              <select
                id="language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.value} value={lang.value}>
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>
          </CardContent>
          <CardFooter className="flex-col gap-4 sm:flex-row sm:justify-between">
            <Button
              type="submit"
              variant="primary"
              disabled={loading || !isTopicValid}
            >
              {loading ? 'Creating...' : 'Create Video'}
            </Button>
            <p className="text-xs text-zinc-500">
              Estimated cost: ~$0.11
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
