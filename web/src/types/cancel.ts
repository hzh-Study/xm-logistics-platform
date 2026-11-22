import type { OrderStatus } from '@/types/order'

export type CancelMode = '直接取消' | '公司确认'
export type CancelStatus = '待公司处理' | '已同意' | '已驳回' | '已直接取消'
export type CancelEvent = '申请' | '直接取消' | '同意' | '驳回'

export interface CancelApplication {
  id: number
  application_no: string
  order_id: number
  order_no: string
  shipper_id: number
  carrier_id: number | null
  mode: CancelMode
  status: CancelStatus
  reason: string
  handled_reason: string
  before_status: OrderStatus
  after_status: OrderStatus | null
  handled_by: number | null
  handled_at: string | null
  created_at: string
}

export interface CancelAudit {
  id: number
  application_id: number
  event: CancelEvent
  actor_id: number
  actor: '货主' | '物流公司'
  from_status: OrderStatus
  to_status: OrderStatus
  reason: string
  detail: string
  created_at: string
}

export interface CancelView {
  application: CancelApplication | null
  audit: CancelAudit[]
}

export interface CancelOptions {
  order_id: number
  status: OrderStatus
  can_cancel: boolean
  mode: CancelMode | null
  message: string
}
