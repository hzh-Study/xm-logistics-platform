import { request } from '@/api/request'
import type { TaskProgress } from '@/types/checkin'

/** 物流公司查看本公司任务的打卡与装货进度。 */
export function getCarrierProgress(taskId: number): Promise<TaskProgress> {
  return request.get<TaskProgress>(`/api/carrier/tasks/${taskId}/progress`)
}

/** 货主只读查看自己订单的运输进度。 */
export function getShipperProgress(orderId: number): Promise<TaskProgress> {
  return request.get<TaskProgress>(`/api/shipper/orders/${orderId}/progress`)
}
