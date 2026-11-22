import { request } from '@/api/request'
import type { TaskProgress } from '@/types/checkin'
import type { ArrivalCheckin, ArrivalNote, UnloadingAnomaly, UnloadingPhoto } from '@/types/signoff'

/** 提交收货地打卡。 */
export function submitArrivalCheckin(
  taskId: number,
  payload: {
    latitude: number
    longitude: number
    arrived_at: string
    photos: string[]
    notes: string
  },
): Promise<ArrivalCheckin> {
  return request.post<ArrivalCheckin>(`/api/driver/tasks/${taskId}/arrival-checkin`, payload)
}

/** 对收货地位置异常打卡提交说明。 */
export function submitArrivalNote(taskId: number, note: string): Promise<ArrivalNote> {
  return request.post<ArrivalNote>(`/api/driver/tasks/${taskId}/arrival-checkin/exception-note`, { note })
}

/** 上传某一卸货阶段的现场照片。 */
export function addUnloadingPhotos(
  taskId: number,
  phase: string,
  paths: string[],
): Promise<UnloadingPhoto> {
  return request.post<UnloadingPhoto>(`/api/driver/tasks/${taskId}/unloading/photos`, { phase, paths })
}

/** 上报卸货异常。 */
export function addUnloadingAnomaly(
  taskId: number,
  kind: string,
  detail: string,
  photos: string[] = [],
): Promise<UnloadingAnomaly> {
  return request.post<UnloadingAnomaly>(`/api/driver/tasks/${taskId}/unloading/anomalies`, {
    kind,
    detail,
    photos,
  })
}

/** 提交签收资料，返回含签收凭证的任务进度。 */
export function submitSignoff(
  taskId: number,
  payload: {
    receiving_condition: string
    received_at: string
    receiver_name: string
    signature_photos: string[]
    vouchers: string[]
    notes: string
  },
): Promise<TaskProgress> {
  return request.post<TaskProgress>(`/api/driver/tasks/${taskId}/signoff`, payload)
}
