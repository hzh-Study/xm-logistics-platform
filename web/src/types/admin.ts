/** 管理员首页运营统计。 */
export interface AdminStats {
  shipper_count: number
  carrier_count: number
  driver_count: number
  vehicle_count: number
  orders_pending_accept: number
  orders_in_transit: number
  orders_completed: number
  orders_exception: number
  pending_certifications: number
}

/** 管理员视角的货主摘要。 */
export interface ShipperSummary {
  account_id: number
  phone: string
  company_name: string
  profile_type: string
  account_status: string
  auth_status: string
}

/** 管理员视角的司机摘要。 */
export interface DriverSummary {
  account_id: number
  phone: string
  driver_name: string
  license_no: string
  carrier_id: number | null
  account_status: string
  auth_status: string
  availability: string
  employment: string
}

/** 管理员视角的车辆摘要。 */
export interface VehicleSummary {
  id: number
  plate_no: string
  carrier_id: number
  vehicle_type: string
  availability: string
  lifecycle: string
  document_status: string
  document_review_status: string
}

/** 统一认证列表中的一条记录。 */
export interface CertItem {
  id: number
  category: CertCategory
  subject_id: number
  subject_name: string
  auth_status: string
  account_status: string
  submitted_at: string | null
  reason: string | null
  detail: string
}

/** 五类认证的类别。 */
export type CertCategory = '货主' | '企业' | '司机' | '驾驶资格' | '车辆证件'

/** 统一审核决策。 */
export type ReviewDecision = '审核通过' | '审核不通过'

/** 一次统一审核的结果。 */
export interface CertReview {
  category: CertCategory
  target_id: number
  decision: ReviewDecision
  reason: string
  actor_id: number
  created_at: string
}

/** 账号状态处置结果。 */
export interface AccountStatusResult {
  account_id: number
  role: string
  account_status: string
}

/** 平台公告出参，channel 表明独立于业务通知通道。 */
export interface Announcement {
  id: number
  title: string
  body: string
  scope: string
  publisher_id: number
  published_at: string
  channel: string
}

/** 平台通知出参。 */
export interface PlatformNotice {
  id: number
  title: string
  body: string
  scope: string
  publisher_id: number
  published_at: string
  channel: string
}
