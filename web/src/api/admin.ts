import { request } from '@/api/request'
import type {
  CarrierSummary,
  CertificationRecord,
} from '@/types/carrier'

/** 列出物流公司，可按认证状态筛选。 */
export function listCarriers(authStatus?: string): Promise<CarrierSummary[]> {
  const query = authStatus ? `?auth_status=${encodeURIComponent(authStatus)}` : ''
  return request.get<CarrierSummary[]>(`/api/admin/carriers${query}`)
}

/** 读取指定物流公司的认证记录。 */
export function fetchCarrierCertifications(
  accountId: number,
): Promise<CertificationRecord[]> {
  return request.get<CertificationRecord[]>(
    `/api/admin/carriers/${accountId}/certifications`,
  )
}

/** 审核通过或驳回企业认证。 */
export function reviewCertification(
  accountId: number,
  decision: '通过' | '驳回',
  reason: string,
): Promise<CertificationRecord> {
  return request.post<CertificationRecord>(
    `/api/admin/carriers/${accountId}/certification/review`,
    { decision, reason },
  )
}

/** 禁用或恢复物流公司账号。 */
export function setCarrierAccountStatus(
  accountId: number,
  accountStatus: '正常使用' | '已禁用',
): Promise<CarrierSummary> {
  return request.post<CarrierSummary>(
    `/api/admin/carriers/${accountId}/status`,
    { account_status: accountStatus },
  )
}
