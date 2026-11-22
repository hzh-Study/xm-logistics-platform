import { request } from '@/api/request'
import type { Order, OrderFilter, PublishInput } from '@/types/order'

/** 发布运输订单。 */
export function publishOrder(data: PublishInput): Promise<Order> {
  return request.post<Order>('/api/shipper/orders', data)
}

/** 读取货主自己的运输订单，可按条件筛选。 */
export function fetchOrders(filter: OrderFilter = {}): Promise<Order[]> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filter)) {
    if (value) params.set(key, value)
  }
  const query = params.toString()
  return request.get<Order[]>(`/api/shipper/orders${query ? `?${query}` : ''}`)
}

/** 读取单条运输订单详情。 */
export function fetchOrder(orderId: number): Promise<Order> {
  return request.get<Order>(`/api/shipper/orders/${orderId}`)
}
