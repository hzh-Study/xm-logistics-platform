import { request } from '@/api/request'
import type { DriverTask } from '@/types/dispatch'

/** 列出派给当前司机的运输任务。 */
export function listDriverTasks(): Promise<DriverTask[]> {
  return request.get<DriverTask[]>('/api/driver/tasks')
}

/** 读取一条派给当前司机的任务详情。 */
export function getDriverTask(taskId: number): Promise<DriverTask> {
  return request.get<DriverTask>(`/api/driver/tasks/${taskId}`)
}

/** 司机确认任务。 */
export function acceptTask(taskId: number): Promise<DriverTask> {
  return request.post<DriverTask>(`/api/driver/tasks/${taskId}/accept`)
}

/** 司机填写原因拒绝任务。 */
export function rejectTask(taskId: number, reason: string): Promise<DriverTask> {
  return request.post<DriverTask>(`/api/driver/tasks/${taskId}/reject`, { reason })
}
