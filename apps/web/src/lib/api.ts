import type {
  UserResponse,
  JobResponse,
  JobDetailResponse,
  JobCreateRequest,
  PaginatedResponse,
} from '@/types/api'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message)
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(
      res.status,
      body?.error?.code || 'UNKNOWN',
      body?.error?.message || res.statusText,
    )
  }

  return res.json()
}

export const api = {
  auth: {
    register: (data: {
      email: string
      password: string
      display_name: string
    }) =>
      apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    login: (data: { email: string; password: string }) =>
      apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    logout: () => apiFetch('/auth/logout', { method: 'POST' }),
    refresh: () => apiFetch('/auth/refresh', { method: 'POST' }),
  },
  users: {
    me: () => apiFetch<UserResponse>('/users/me'),
  },
  jobs: {
    create: (data: JobCreateRequest) =>
      apiFetch<JobResponse>('/jobs', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    list: (params?: { status?: string; cursor?: string }) => {
      const query = new URLSearchParams(
        Object.entries(params || {}).filter(
          (entry): entry is [string, string] => entry[1] != null,
        ),
      ).toString()
      return apiFetch<PaginatedResponse<JobResponse>>(
        `/jobs${query ? `?${query}` : ''}`,
      )
    },
    get: (id: string) => apiFetch<JobDetailResponse>(`/jobs/${id}`),
    cancel: (id: string) => apiFetch(`/jobs/${id}`, { method: 'DELETE' }),
  },
  teams: {
    list: () => apiFetch<PaginatedResponse<any>>('/teams'),
    create: (data: { name: string }) =>
      apiFetch('/teams', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) => apiFetch(`/teams/${id}`),
    invite: (teamId: string, data: { email: string; role: string }) =>
      apiFetch(`/teams/${teamId}/members/invite`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  channels: {
    list: () => apiFetch<any[]>('/channels'),
    connect: () =>
      apiFetch<{ auth_url: string }>('/channels/connect', { method: 'POST' }),
    disconnect: (id: string) =>
      apiFetch(`/channels/${id}`, { method: 'DELETE' }),
  },
  topics: {
    trending: () => apiFetch<any>('/topics/trending'),
    quickCreate: (topic: string) =>
      apiFetch('/topics/quick-create', {
        method: 'POST',
        body: JSON.stringify({ topic_title: topic }),
      }),
  },
  billing: {
    plans: () => apiFetch<any[]>('/billing/plans'),
    subscription: () => apiFetch<any>('/billing/subscription'),
    checkout: (plan: string) =>
      apiFetch<{ checkout_url: string }>('/billing/checkout', {
        method: 'POST',
        body: JSON.stringify({ plan }),
      }),
    portal: () =>
      apiFetch<{ url: string }>('/billing/portal', { method: 'POST' }),
  },
  videos: {
    list: () => apiFetch<PaginatedResponse<any>>('/videos'),
    get: (id: string) => apiFetch<any>(`/videos/${id}`),
    download: (id: string) =>
      apiFetch<{ url: string }>(`/videos/${id}/download`),
    delete: (id: string) => apiFetch(`/videos/${id}`, { method: 'DELETE' }),
  },
}
