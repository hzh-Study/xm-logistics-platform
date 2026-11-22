import { request } from '@/api/request'
import type { CurrentUser } from '@/types/auth'
import type {
  BusinessAccess,
  Capabilities,
  CertificationRecord,
  CertificationSubmitPayload,
  CertificationView,
} from '@/types/carrier'

/** 注册物流公司账号。 */
export function registerCarrier(
  phone: string,
  password: string,
  companyName: string,
): Promise<CurrentUser> {
  return request.post<CurrentUser>('/api/carrier/register', {
    phone,
    password,
    company_name: companyName,
  })
}

/** 提交或重新提交企业认证资料。 */
export function submitCertification(
  payload: CertificationSubmitPayload,
): Promise<CertificationRecord> {
  return request.post<CertificationRecord>('/api/carrier/certification', payload)
}

/** 读取当前认证状态与全部认证记录。 */
export function fetchCertification(): Promise<CertificationView> {
  return request.get<CertificationView>('/api/carrier/certification')
}

/** 读取承运业务能力开关。 */
export function fetchCapabilities(): Promise<Capabilities> {
  return request.get<Capabilities>('/api/carrier/capabilities')
}

/** 校验是否可进入承运业务。 */
export function fetchBusinessAccess(): Promise<BusinessAccess> {
  return request.get<BusinessAccess>('/api/carrier/business-access')
}
