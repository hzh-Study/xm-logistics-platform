import { request } from '@/api/request'
import type { AdminCertification } from '@/types/shipper'

/** 管理员列出货主认证记录。 */
export function fetchShipperCertifications(): Promise<AdminCertification[]> {
  return request.get<AdminCertification[]>('/api/admin/shipper-certifications')
}

/** 管理员审核通过或驳回，驳回必须带原因。 */
export function reviewShipperCertification(
  certificationId: number,
  decision: '审核通过' | '审核不通过',
  rejectionReason?: string,
): Promise<AdminCertification> {
  return request.post<AdminCertification>(
    `/api/admin/shipper-certifications/${certificationId}/review`,
    { decision, rejection_reason: rejectionReason },
  )
}
