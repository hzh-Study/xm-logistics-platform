import type { ApiErrorEnvelope } from '@/types/api'

const BASE = import.meta.env.VITE_API_BASE ?? ''

/** 归一后的错误：保留 code 与 details 供界面展示驳回原因。 */
export class ApiError extends Error {
  code: string
  details: unknown

  constructor(code: string, message: string, details: unknown) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.details = details
  }
}

/** 请求实例：统一注入凭证与 CSRF，归一错误信封。 */
class RequestClient {
  private csrfToken = ''

  setCsrfToken(token: string): void {
    this.csrfToken = token
  }

  clearCsrfToken(): void {
    this.csrfToken = ''
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const method = (init.method ?? 'GET').toUpperCase()
    const headers = new Headers(init.headers)
    headers.set('Content-Type', 'application/json')
    if (method !== 'GET' && method !== 'HEAD' && this.csrfToken) {
      headers.set('X-CSRF-Token', this.csrfToken)
    }
    const response = await fetch(`${BASE}${path}`, {
      ...init,
      method,
      headers,
      credentials: 'include',
    })
    if (!response.ok) {
      let envelope: ApiErrorEnvelope | undefined
      try {
        envelope = (await response.json()) as ApiErrorEnvelope
      } catch {
        // 响应非 JSON 时按通用错误处理
      }
      throw new ApiError(
        envelope?.error?.code ?? `http_${response.status}`,
        envelope?.error?.message ?? `请求失败（${response.status}）`,
        envelope?.error?.details,
      )
    }
    if (response.status === 204) {
      return undefined as T
    }
    return (await response.json()) as T
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path)
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  }
}

export const request = new RequestClient()
