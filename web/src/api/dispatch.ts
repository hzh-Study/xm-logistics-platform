import { request } from '@/api/request'
import type { Order } from '@/types/order'
import type {
  DispatchHistory,
  RedispatchPayload,
  TaskCreatePayload,
  TransportTask,
} from '@/types/dispatch'

/** 列出本公司承接的订单，供派单挑选。 */
export function listCarrierOrders(): Promise<Order[]> {
  return request.get<Order[]>('/api/carrier/orders')
}

/** 列出本公司运输任务，可按状态与订单筛选。 */
export function listTasks(status?: string, orderId?: number): Promise<TransportTask[]> {
  const query = new URLSearchParams()
  if (status) query.set('status_filter', status)
  if (orderId) query.set('order_id', String(orderId))
  const suffix = query.toString()
  return request.get<TransportTask[]>(`/api/carrier/tasks${suffix ? `?${suffix}` : ''}`)
}

/** 为已承接订单派单，创建运输任务。 */
export function createTask(payload: TaskCreatePayload): Promise<TransportTask> {
  return request.post<TransportTask>('/api/carrier/tasks', payload)
}

/** 未起运重新派单，更换执行司机 / 车辆。 */
export function redispatchTask(taskId: number, payload: RedispatchPayload): Promise<TransportTask> {
  return request.post<TransportTask>(`/api/carrier/tasks/${taskId}/redispatch`, payload)
}

/** 读取一条任务的派单历史。 */
export function dispatchHistory(taskId: number): Promise<DispatchHistory[]> {
  return request.get<DispatchHistory[]>(`/api/carrier/tasks/${taskId}/dispatch-history`)
}
