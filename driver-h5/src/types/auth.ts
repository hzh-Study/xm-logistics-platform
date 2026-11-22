/** 当前用户公开信息。 */
export interface CurrentUser {
  id: number
  phone: string
  role: '货主' | '物流公司' | '司机' | '管理员'
  account_status: string
  auth_status: string
}

/** /me 响应：当前用户与可恢复的 CSRF token。 */
export interface MeResult extends CurrentUser {
  csrf_token: string
}

/** 登录响应。 */
export interface LoginResult {
  user: CurrentUser
  csrf_token: string
}
