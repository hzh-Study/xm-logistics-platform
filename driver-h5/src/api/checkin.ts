import { request } from '@/api/request'
import type {
  Checkin,
  CheckinPayload,
  ExceptionNote,
  LoadingAnomaly,
  LoadingPhoto,
  TaskProgress,
} from '@/types/checkin'

/** 提交发货地打卡。 */
export function submitCheckin(taskId: number, payload: CheckinPayload): Promise<Checkin> {
  return request.post<Checkin>(`/api/driver/tasks/${taskId}/checkin`, payload)
}

/** 对位置异常打卡提交说明。 */
export function submitExceptionNote(taskId: number, note: string): Promise<ExceptionNote> {
  return request.post<ExceptionNote>(`/api/driver/tasks/${taskId}/checkin/exception-note`, { note })
}

/** 上传某一装货阶段的现场照片。 */
export function addLoadingPhotos(taskId: number, phase: string, paths: string[]): Promise<LoadingPhoto> {
  return request.post<LoadingPhoto>(`/api/driver/tasks/${taskId}/loading/photos`, { phase, paths })
}

/** 上报装货异常。 */
export function addLoadingAnomaly(
  taskId: number,
  kind: string,
  detail: string,
  photos: string[] = [],
): Promise<LoadingAnomaly> {
  return request.post<LoadingAnomaly>(`/api/driver/tasks/${taskId}/loading/anomalies`, {
    kind,
    detail,
    photos,
  })
}

/** 货物与车辆核对完成后开始运输。 */
export function startTransport(
  taskId: number,
  payload: { cargo_confirmed: boolean; vehicle_confirmed: boolean; notes: string },
): Promise<TaskProgress> {
  return request.post<TaskProgress>(`/api/driver/tasks/${taskId}/start-transport`, payload)
}

/** 读取本人任务的打卡与装货进度。 */
export function getDriverProgress(taskId: number): Promise<TaskProgress> {
  return request.get<TaskProgress>(`/api/driver/tasks/${taskId}/progress`)
}
