import { request } from '@/api/request'
import type { LoginResult, MeResult } from '@/types/auth'

/** 登录并下发会话与 CSRF token。 */
export function login(phone: string, password: string): Promise<LoginResult> {
  return request.post<LoginResult>('/api/auth/login', { phone, password })
}

/** 读取当前用户与 CSRF，供刷新后恢复。 */
export function fetchMe(): Promise<MeResult> {
  return request.get<MeResult>('/api/auth/me')
}

/** 退出并撤销会话。 */
export function logout(): Promise<void> {
  return request.post<void>('/api/auth/logout')
}
