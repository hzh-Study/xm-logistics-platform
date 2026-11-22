/** 发货地打卡记录；位置异常是告警而非驳回。 */
export interface Checkin {
  id: number
  task_id: number
  task_no: string
  latitude: number
  longitude: number
  arrived_at: string
  photos: string[]
  notes: string
  position_status: '正常' | '位置异常'
  distance_m: number | null
  warning: string
  exception_note_required: boolean
  created_at: string
}

/** 位置异常说明，只读追加。 */
export interface ExceptionNote {
  id: number
  checkin_id: number
  note: string
  created_at: string
}

/** 一批装货阶段照片。 */
export interface LoadingPhoto {
  id: number
  task_id: number
  phase: '装货前' | '装货中' | '装货完成'
  paths: string[]
  created_at: string
}

/** 一条装货异常记录。 */
export interface LoadingAnomaly {
  id: number
  task_id: number
  kind: '数量不符' | '货损' | '超载'
  detail: string
  photos: string[]
  created_at: string
}

/** 起运前货物与车辆确认。 */
export interface DepartureConfirmation {
  id: number
  task_id: number
  cargo_confirmed: boolean
  vehicle_confirmed: boolean
  notes: string
  created_at: string
}

/** 任务进度：物流公司与货主只读查看，不含运费报价。 */
export interface TaskProgress {
  task_id: number
  task_no: string
  order_id: number
  order_no: string
  status: string
  task_status: string
  order_status: string
  planned_load_at: string
  planned_deliver_at: string
  checkins: Checkin[]
  exception_notes: ExceptionNote[]
  loading_photos: LoadingPhoto[]
  loading_anomalies: LoadingAnomaly[]
  confirmation: DepartureConfirmation | null
}
