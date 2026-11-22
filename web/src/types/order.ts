/** 运输订单状态取值。 */
export type OrderStatus =
  | '待承接'
  | '已承接'
  | '运输中'
  | '已完成'
  | '取消处理中'
  | '已取消'
  | '异常处理中'

/** 运费报价方式。 */
export type QuoteMethod = '固定' | '可协商' | '其他'

/** 发货来源。 */
export type ShippingSource = '仓库' | '临时地址'

/** 固化的发货快照。 */
export interface ShippingSnapshot {
  source: ShippingSource
  warehouse_id: number | null
  name: string
  contact: string
  phone: string
  province: string
  city: string
  district: string
  detail_address: string
  type: string
}

/** 固化的收货快照。 */
export interface ReceivingSnapshot {
  name: string
  contact: string
  phone: string
  province: string
  city: string
  district: string
  detail_address: string
}

/** 发布运输订单入参；未填字段沿用服务端默认值。 */
export interface PublishInput {
  cargo_name: string
  cargo_type?: string
  quantity?: string
  weight?: string
  volume?: string
  packaging?: string
  cargo_photos?: string[]
  cargo_remarks?: string
  shipping_source?: ShippingSource
  warehouse_id?: number
  shipping_name?: string
  shipping_contact?: string
  shipping_phone?: string
  shipping_province?: string
  shipping_city?: string
  shipping_district?: string
  shipping_detail_address?: string
  receiving_name?: string
  receiving_contact?: string
  receiving_phone?: string
  receiving_province?: string
  receiving_city?: string
  receiving_district?: string
  receiving_detail_address?: string
  vehicle_type?: string
  vehicle_length?: string
  load_requirement?: string
  cold_chain?: boolean
  rain_protection?: boolean
  enclosed_body?: boolean
  special_loading?: boolean
  other_services?: string
  transport_remarks?: string
  quote_method?: QuoteMethod
  quote_amount_yuan?: string
  accept_bargain?: boolean
  quote_remarks?: string
}

/** 运输订单完整出参（运费报价仅对货主与物流公司可见）。 */
export interface Order {
  id: number
  order_no: string
  shipper_id: number
  cargo_name: string
  status: OrderStatus
  carrier_id: number | null
  accepted_at: string | null
  created_at: string
  cargo_type: string
  quantity: string
  weight: string
  volume: string
  packaging: string
  cargo_photos: string[]
  cargo_remarks: string
  shipping_snapshot: ShippingSnapshot
  receiving_snapshot: ReceivingSnapshot
  vehicle_type: string
  vehicle_length: string
  load_requirement: string
  cold_chain: boolean
  rain_protection: boolean
  enclosed_body: boolean
  special_loading: boolean
  other_services: string
  transport_remarks: string
  quote_method: QuoteMethod
  quote_amount_yuan: string
  accept_bargain: boolean
  quote_remarks: string
}

/** 订单列表筛选条件。 */
export interface OrderFilter {
  order_no?: string
  status?: OrderStatus
  cargo_name?: string
  shipping_place?: string
  receiving_place?: string
  published_from?: string
  published_to?: string
}

/** 公共订单池筛选条件（池内只含待承接货源）。 */
export interface PoolFilter {
  shipping_place?: string
  receiving_place?: string
  cargo_type?: string
  vehicle_type?: string
  weight?: string
  published_from?: string
  published_to?: string
  quote_min_yuan?: string
  quote_max_yuan?: string
}
