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

/** 平台异常类别。 */
export type PlatformExceptionCategory =
  | '投诉'
  | '订单纠纷'
  | '公司违规'
  | '司机违规'
  | '车辆异常'
  | '任务长期未完成'
  | '费用纠纷'

/** 平台异常处理结果。 */
export type PlatformResult = '已处理' | '已调解' | '已处罚' | '已驳回' | '已归档'

/** 一条平台异常登记记录（只读追加）。 */
export interface PlatformException {
  id: number
  exception_no: string
  category: PlatformExceptionCategory
  subject: string
  detail: string
  subject_account_id: number | null
  order_id: number | null
  task_id: number | null
  vehicle_id: number | null
  actor: string
  created_at: string
}

/** 一条平台异常处理记录：带 actor 角色、原因、结果与时间。 */
export interface PlatformHandling {
  id: number
  handling_no: string
  exception_id: number
  result: PlatformResult
  reason: string
  detail: string
  actor: string
  actor_id: number
  order_status: string | null
  task_status: string | null
  handled_at: string
  created_at: string
}

/** 平台异常与全部追加处理记录的只读视图。 */
export interface PlatformExceptionView {
  exception: PlatformException
  handling_records: PlatformHandling[]
}

/** 一条车辆转籍历史：保留转出 / 转入归属。 */
export interface VehicleTransfer {
  id: number
  transfer_no: string
  vehicle_id: number
  plate_no: string
  before_carrier_id: number
  after_carrier_id: number
  reason: string
  actor: string
  actor_id: number
  created_at: string
}
