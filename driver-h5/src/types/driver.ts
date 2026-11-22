/** 司机端身份绑定与工作台相关类型。 */

export type AuthStatus = '未提交' | '待审核' | '审核通过' | '审核不通过'

export interface Onboarding {
  must_change_password: boolean
  binding_complete: boolean
  company_name: string
  auth_status: AuthStatus
  blocked_reason: string
}

export interface DriverSelf {
  account_id: number
  phone: string
  name: string
  company_name: string
  auth_status: AuthStatus
  account_status: string
  availability: string
  employment: string
  binding_complete: boolean
  must_change_password: boolean
}

export interface DriverBindingPayload {
  name: string
  id_number: string
  license_no: string
  license_type: string
  license_expiry: string
}
