/** 收货地打卡记录；位置异常是告警而非驳回。 */
export interface ArrivalCheckin {
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

/** 收货地位置异常说明，只读追加。 */
export interface ArrivalNote {
  id: number
  checkin_id: number
  note: string
  created_at: string
}

/** 一批卸货阶段照片。 */
export interface UnloadingPhoto {
  id: number
  task_id: number
  phase: '卸货前' | '卸货中' | '卸货完成'
  paths: string[]
  created_at: string
}

/** 一条卸货异常记录。 */
export interface UnloadingAnomaly {
  id: number
  task_id: number
  kind: '货损' | '数量不符' | '拒收'
  detail: string
  photos: string[]
  created_at: string
}

/** 签收凭证：公司据以确认完成，货主只读。 */
export interface SignoffVoucher {
  id: number
  voucher_no: string
  task_id: number
  task_no: string
  order_id: number
  receiving_condition: '完好' | '货损' | '数量不符' | '其他'
  received_at: string
  receiver_name: string
  signature_photos: string[]
  vouchers: string[]
  notes: string
  created_at: string
}

/** 公司依据签收凭证作出的完成确认，只读追加。 */
export interface SignoffConfirmation {
  id: number
  task_id: number
  voucher_id: number
  carrier_account_id: number
  notes: string
  created_at: string
}

/** 货主补录的收货快照坐标。 */
export interface ReceivingCoordinate {
  order_id: number
  latitude: number
  longitude: number
}
