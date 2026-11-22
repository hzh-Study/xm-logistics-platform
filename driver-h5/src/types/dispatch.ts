/** 司机任务状态取值。 */
export type DriverTaskStatus =
  | '待司机确认'
  | '待装货'
  | '运输中'
  | '待签收'
  | '待确认完成'
  | '已完成'
  | '异常'
  | '已拒绝'

/** 司机可见的地点快照。 */
export interface DriverPlace {
  name: string
  contact: string
  phone: string
  province: string
  city: string
  district: string
  detail_address: string
}

/** 司机任务详情：仅执行所需字段，不含运费报价。 */
export interface DriverTask {
  task_id: number
  task_no: string
  order_id: number
  order_no: string
  status: DriverTaskStatus
  planned_load_at: string
  planned_deliver_at: string
  notes: string
  cargo_name: string
  cargo_type: string
  quantity: string
  weight: string
  volume: string
  packaging: string
  cargo_photos: string[]
  cargo_remarks: string
  shipping: DriverPlace
  receiving: DriverPlace
  vehicle_type: string
  vehicle_length: string
  load_requirement: string
  cold_chain: boolean
  rain_protection: boolean
  enclosed_body: boolean
  special_loading: boolean
  other_services: string
  transport_remarks: string
  vehicle_plate: string
  vehicle_type_actual: string
  vehicle_length_m: number
  vehicle_max_load_kg: number
  carrier_company: string
  accepted_at: string | null
  reject_reason: string
  created_at: string
}
