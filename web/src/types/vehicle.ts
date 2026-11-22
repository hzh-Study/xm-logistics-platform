/** 车辆管理相关类型。 */

export type VehicleType = '厢式货车' | '平板货车' | '高栏货车' | '冷藏车' | '其他'
export type OwnerType = '公司' | '司机'
export type Availability = '可用' | '占用中' | '暂停使用'
export type Lifecycle = '在册' | '维修中' | '已停用'
export type DocumentStatus = '待审核' | '有效' | '已过期'

/** 车辆：可用性与生命周期是两个独立维度。 */
export interface Vehicle {
  id: number
  plate_no: string
  vehicle_type: VehicleType
  length_m: number
  max_load_kg: number
  owner_type: OwnerType
  actual_owner: string
  owner_driver_id: number | null
  current_driver_id: number | null
  current_driver: string
  availability: Availability
  lifecycle: Lifecycle
  document_status: DocumentStatus
  assignable: boolean
  created_at: string
}

export interface VehicleCreatePayload {
  plate_no: string
  vehicle_type: VehicleType
  length_m: number
  max_load_kg: number
  owner_type: OwnerType
  owner_driver_id?: number | null
  document_status?: DocumentStatus
}
