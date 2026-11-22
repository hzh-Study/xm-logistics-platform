import { request } from '@/api/request'
import type { Anomaly, AnomalyPayload, ExceptionView } from '@/types/exception'

/** 司机上报在途异常与现场照片。 */
export function submitAnomaly(taskId: number, payload: AnomalyPayload): Promise<Anomaly> {
  return request.post<Anomaly>(`/api/driver/tasks/${taskId}/anomalies`, payload)
}

/** 司机读取本人任务的异常与处理记录。 */
export function getDriverExceptions(taskId: number): Promise<ExceptionView> {
  return request.get<ExceptionView>(`/api/driver/tasks/${taskId}/exceptions`)
}
