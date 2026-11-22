import type { CurrentUser } from '@/types/auth'

/** 认证状态取值。 */
export type AuthStatus = '未提交' | '待审核' | '审核通过' | '审核不通过'

/** 单条认证提交及其审核结果。 */
export interface Certification {
  id: number
  cert_type: '个人' | '企业'
  name: string
  id_number: string
  contact_phone: string
  documents: string[]
  status: '待审核' | '审核通过' | '审核不通过'
  rejection_reason: string | null
  reviewer_id: number | null
  reviewed_at: string | null
  submitted_at: string
}

/** 货主认证状态视图。 */
export interface CertificationView {
  auth_status: AuthStatus
  current: Certification | null
  history: Certification[]
}

/** 认证资料提交入参。 */
export interface CertificationInput {
  cert_type: '个人' | '企业'
  name: string
  id_number: string
  contact_phone: string
  documents: string[]
}

/** 管理员视角的一条货主认证记录。 */
export interface AdminCertification {
  account_id: number
  phone: string
  auth_status: AuthStatus
  account_status: string
  certification_id: number | null
  cert_type: '个人' | '企业' | null
  name: string | null
  id_number: string | null
  contact_phone: string | null
  documents: string[]
  status: '待审核' | '审核通过' | '审核不通过' | null
  rejection_reason: string | null
  submitted_at: string | null
  reviewed_at: string | null
}

/** 站内通知。 */
export interface ShipperNotification {
  id: number
  kind: string
  title: string
  body: string
  related_id: number | null
  created_at: string
}

/** 运输订单出参定义在订单领域模型中。 */
export type { Order } from '@/types/order'

/** 注册响应，与登录响应同形。 */
export interface RegisterResult {
  user: CurrentUser
  csrf_token: string
}
