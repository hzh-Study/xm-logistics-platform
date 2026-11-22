/** 物流公司认证与审核相关类型。 */

export type AuthStatus = '未提交' | '待审核' | '审核通过' | '审核不通过'
export type AccountStatus = '正常使用' | '已禁用' | '已注销'

export interface CertificationRecord {
  id: number
  account_id: number
  kind: '提交' | '审核'
  decision: '' | '审核通过' | '审核不通过'
  company_name: string
  license_no: string
  license_path: string
  legal_person: string
  contact_name: string
  contact_phone: string
  qualification_path: string
  note: string
  reason: string
  actor: '物流公司' | '管理员'
  replaced_by: number | null
  created_at: string
}

export interface CertificationView {
  auth_status: AuthStatus
  account_status: AccountStatus
  latest: CertificationRecord | null
  records: CertificationRecord[]
}

export interface Capabilities {
  can_accept_orders: boolean
  can_dispatch: boolean
  can_manage_drivers: boolean
  can_manage_vehicles: boolean
  reasons: string[]
}

export interface BusinessAccess {
  company_name: string
  auth_status: AuthStatus
  capabilities: Capabilities
}

export interface CarrierSummary {
  account_id: number
  phone: string
  company_name: string
  license_no: string
  account_status: AccountStatus
  auth_status: AuthStatus
}

export interface CertificationSubmitPayload {
  company_name: string
  license_no: string
  license_path: string
  legal_person: string
  contact_name: string
  contact_phone: string
  qualification_path: string
  note?: string
}
