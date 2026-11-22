/** 在途异常类型。 */
export type AnomalyKind = '故障' | '事故' | '封路' | '拥堵' | '货物异常' | '预计延误' | '其他'

/** 异常处理结果。 */
export type HandlingResult =
  | '继续运输'
  | '调整送达时间'
  | '更换车辆'
  | '更换司机'
  | '重新安排运输'
  | '终止运输'

/** 一条在途异常记录，只读追加。 */
export interface Anomaly {
  id: number
  anomaly_no: string
  task_id: number
  task_no: string
  order_id: number
  kind: AnomalyKind | string
  detail: string
  photos: string[]
  occurred_at: string
  started: boolean
  actor: string
  created_at: string
}

/** 一条异常处理记录，含 actor 角色、处理时间与最终结果。 */
export interface HandlingRecord {
  id: number
  handling_no: string
  anomaly_id: number
  task_id: number
  task_no: string
  result: HandlingResult | string
  detail: string
  reason: string
  actor: string
  before_driver_account_id: number | null
  before_driver_name: string
  before_vehicle_id: number | null
  before_vehicle_plate: string
  after_driver_account_id: number | null
  after_driver_name: string
  after_vehicle_id: number | null
  after_vehicle_plate: string
  before_deliver_at: string | null
  after_deliver_at: string | null
  order_status: string
  task_status: string
  handled_at: string
  created_at: string
}

/** 任务 / 订单的在途异常与处理记录只读视图。 */
export interface ExceptionView {
  task_id: number
  task_no: string
  order_id: number
  order_no: string
  anomalies: Anomaly[]
  handling_records: HandlingRecord[]
}

/** 司机上报在途异常入参。 */
export interface AnomalyPayload {
  kind: AnomalyKind
  detail: string
  photos: string[]
  occurred_at: string
}

/** 物流公司追加异常处理记录入参。 */
export interface HandlingPayload {
  result: HandlingResult
  detail: string
  new_vehicle_id?: number
  new_driver_account_id?: number
  adjusted_deliver_at?: string
}
