import { request } from '@/api/request'
import type { CancelApplication, CancelOptions, CancelView } from '@/types/cancel'

/** 货主读取订单的取消入口可用性。 */
export function getCancelOptions(orderId: number): Promise<CancelOptions> {
  return request.get<CancelOptions>(`/api/shipper/orders/${orderId}/cancel-options`)
}

/** 货主按订单状态申请取消。 */
export function applyCancel(orderId: number, reason?: string): Promise<CancelApplication> {
  return request.post<CancelApplication>(`/api/shipper/orders/${orderId}/cancel`, { reason })
}

/** 货主查看取消申请与全过程留痕。 */
export function getCancelView(orderId: number): Promise<CancelView> {
  return request.get<CancelView>(`/api/shipper/orders/${orderId}/cancel`)
}

/** 物流公司列出本公司承运订单上的取消申请。 */
export function listCancelApplications(): Promise<CancelApplication[]> {
  return request.get<CancelApplication[]>('/api/carrier/cancel-applications')
}

/** 物流公司读取一条取消申请的当前态与留痕。 */
export function getCancelApplication(applicationId: number): Promise<CancelView> {
  return request.get<CancelView>(`/api/carrier/cancel-applications/${applicationId}`)
}

/** 物流公司同意取消申请。 */
export function agreeCancel(applicationId: number): Promise<CancelApplication> {
  return request.post<CancelApplication>(`/api/carrier/cancel-applications/${applicationId}/agree`)
}

/** 物流公司驳回取消申请，原因必填。 */
export function rejectCancel(applicationId: number, reason: string): Promise<CancelApplication> {
  return request.post<CancelApplication>(`/api/carrier/cancel-applications/${applicationId}/reject`, {
    reason,
  })
}
