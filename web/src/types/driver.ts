/** 司机管理相关类型。 */

export type AuthStatus = '未提交' | '待审核' | '审核通过' | '审核不通过'
export type AccountStatus = '正常使用' | '已禁用' | '已注销'
export type Availability = '可派单' | '任务占用中' | '暂停接单'
export type Employment = '在职' | '离职'

export interface Driver {
  account_id: number
  phone: string
  name: string
  auth_status: AuthStatus
  account_status: AccountStatus
  id_number: string
  license_no: string
  license_type: string
  license_expiry: string
  qualification: string
  availability: Availability
  employment: Employment
  departure_date: string | null
  binding_complete: boolean
  must_change_password: boolean
  current_vehicle: string
  current_task: string
  historical_task_count: number
  can_dispatch_new: boolean
  can_continue_in_flight: boolean
}

export interface DriverIdentityRecord {
  id: number
  account_id: number
  name: string
  id_number: string
  license_no: string
  license_type: string
  license_expiry: string
  reason: string
  actor: string
  replaced_by: number | null
  created_at: string
}

export interface DriverCreatePayload {
  phone: string
  password: string
  name: string
  id_number?: string
  license_no?: string
  license_type?: string
  license_expiry?: string
}

export interface DriverUpdatePayload {
  name: string
  id_number?: string
  license_no?: string
  license_type?: string
  license_expiry?: string
}
