import { request } from '@/api/request'
import type { Order, OrderFilter, PoolFilter, PublishInput } from '@/types/order'

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

/** 读取公共订单池中的待承接货源，可按多维条件筛选。 */
export function fetchPool(filter: PoolFilter = {}): Promise<Order[]> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filter)) {
    if (value) params.set(key, value)
  }
  const query = params.toString()
  return request.get<Order[]>(`/api/carrier/order-pool${query ? `?${query}` : ''}`)
}

/** 读取公共订单池中一条货源的完整详情。 */
export function fetchPoolOrder(orderId: number): Promise<Order> {
  return request.get<Order>(`/api/carrier/order-pool/${orderId}`)
}

/** 先到先得承接货源，成功后订单移出公共池并归属当前物流公司。 */
export function acceptOrder(orderId: number): Promise<Order> {
  return request.post<Order>(`/api/carrier/order-pool/${orderId}/accept`)
}
