export interface UserResponse {
  id: string
  email: string
  display_name: string
  role: string
  default_lang: string
  subscription?: {
    plan: string
    status: string
    videos_used: number
    videos_limit: number
  }
}

export interface JobResponse {
  id: string
  topic: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'canceled'
  progress_pct: number
  current_stage: string | null
  created_at: string
  completed_at: string | null
  cost_usd: number
}

export interface StageInfo {
  name: string
  status: string
  duration_ms: number | null
}

export interface JobDetailResponse extends JobResponse {
  stages: StageInfo[]
  error_message: string | null
}

export interface JobCreateRequest {
  topic: string
  context?: string
  language?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  next_cursor: string | null
  has_more: boolean
}
