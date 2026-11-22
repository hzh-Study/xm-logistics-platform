/** 仓库状态取值。 */
export type WarehouseStatus = '正常' | '停用'

/** 仓库出参，location 为省市区与详细地址的拼接。 */
export interface Warehouse {
  id: number
  shipper_id: number
  name: string
  location: string
  contact: string
  phone: string
  province: string
  city: string
  district: string
  detail_address: string
  type: string
  remarks: string
  status: WarehouseStatus
  created_at: string
  updated_at: string
}

/** 仓库新增 / 修改入参。 */
export interface WarehouseInput {
  name: string
  contact: string
  phone: string
  province: string
  city: string
  district: string
  detail_address: string
  type: string
  remarks: string
}
