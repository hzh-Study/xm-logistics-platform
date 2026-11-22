import { request } from '@/api/request'
import type { ReceivingCoordinate } from '@/types/signoff'
import type { TaskProgress } from '@/types/checkin'

/** 物流公司依据签收凭证确认任务完成。 */
export function confirmSignoff(
  taskId: number,
  payload: { confirmed: boolean; notes: string },
): Promise<TaskProgress> {
  return request.post<TaskProgress>(`/api/carrier/tasks/${taskId}/signoff/confirm`, payload)
}

/** 货主补录收货快照坐标（运输前可用）。 */
export function setReceivingCoordinate(
  orderId: number,
  latitude: number,
  longitude: number,
): Promise<ReceivingCoordinate> {
  return request.post<ReceivingCoordinate>(`/api/shipper/orders/${orderId}/receiving-coordinate`, {
    latitude,
    longitude,
  })
}
