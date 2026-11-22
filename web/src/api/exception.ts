import { request } from '@/api/request'
import type { ExceptionView, HandlingPayload, HandlingRecord } from '@/types/exception'

/** 物流公司读取本公司任务的异常与处理记录。 */
export function getCarrierExceptions(taskId: number): Promise<ExceptionView> {
  return request.get<ExceptionView>(`/api/carrier/tasks/${taskId}/exceptions`)
}

/** 物流公司追加异常处理记录。 */
export function handleException(
  taskId: number,
  anomalyId: number,
  payload: HandlingPayload,
): Promise<HandlingRecord> {
  return request.post<HandlingRecord>(
    `/api/carrier/tasks/${taskId}/exceptions/${anomalyId}/handle`,
    payload,
  )
}
