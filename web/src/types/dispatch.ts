/** 运输任务状态取值。 */
export type TaskStatus =
  | '待司机确认'
  | '待装货'
  | '运输中'
  | '待签收'
  | '待确认完成'
  | '已完成'
  | '异常'
  | '已拒绝'

/** 物流公司视角的运输任务。 */
export interface TransportTask {
  id: number
  task_no: string
  order_id: number
  order_no: string
  carrier_id: number
  driver_account_id: number
  driver_name: string
  driver_phone: string
  vehicle_id: number
  vehicle_plate: string
  status: TaskStatus
  planned_load_at: string
  planned_deliver_at: string
  notes: string
  reject_reason: string
  accepted_at: string | null
  created_at: string
}

/** 一条派单 / 重新派单 / 拒绝留痕。 */
export interface DispatchHistory {
  id: number
  dispatch_no: string
  order_id: number
  task_id: number
  action: '派单' | '重新派单' | '司机拒绝'
  original_driver_account_id: number | null
  original_driver_name: string
  original_vehicle_id: number | null
  original_vehicle_plate: string
  new_driver_account_id: number | null
  new_driver_name: string
  new_vehicle_id: number | null
  new_vehicle_plate: string
  reason: string
  actor: string
  replaced_by: number | null
  created_at: string
}

/** 派单入参。 */
export interface TaskCreatePayload {
  order_id: number
  driver_account_id: number
  vehicle_id: number
  planned_load_at: string
  planned_deliver_at: string
  notes: string
}

/** 未起运重新派单入参。 */
export interface RedispatchPayload {
  driver_account_id: number
  vehicle_id: number
  reason: string
}
