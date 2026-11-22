import { request } from '@/api/request'
import type {
  Availability,
  AccountStatus,
  Driver,
  DriverCreatePayload,
  DriverIdentityRecord,
  DriverUpdatePayload,
  Employment,
} from '@/types/driver'

export interface DriverFilters {
  availability?: Availability
  employment?: Employment
  account_status?: AccountStatus
}

/** 列出本公司司机，可按三类独立状态筛选。 */
export function listDrivers(filters: DriverFilters = {}): Promise<Driver[]> {
  const query = new URLSearchParams()
  if (filters.availability) query.set('availability', filters.availability)
  if (filters.employment) query.set('employment', filters.employment)
  if (filters.account_status) query.set('account_status', filters.account_status)
  const suffix = query.toString()
  return request.get<Driver[]>(`/api/carrier/drivers${suffix ? `?${suffix}` : ''}`)
}

/** 创建归属本公司的司机账号。 */
export function createDriver(payload: DriverCreatePayload): Promise<Driver> {
  return request.post<Driver>('/api/carrier/drivers', payload)
}

/** 读取一名本公司司机资料。 */
export function getDriver(accountId: number): Promise<Driver> {
  return request.get<Driver>(`/api/carrier/drivers/${accountId}`)
}

/** 修改司机基本资料。 */
export function updateDriver(accountId: number, payload: DriverUpdatePayload): Promise<Driver> {
  return request.put<Driver>(`/api/carrier/drivers/${accountId}`, payload)
}

/** 设置接单可用性。 */
export function setDriverAvailability(accountId: number, availability: Availability): Promise<Driver> {
  return request.post<Driver>(`/api/carrier/drivers/${accountId}/availability`, { availability })
}

/** 设置雇佣关系。 */
export function setDriverEmployment(accountId: number, employment: Employment): Promise<Driver> {
  return request.post<Driver>(`/api/carrier/drivers/${accountId}/employment`, { employment })
}

/** 设置司机账号状态。 */
export function setDriverAccountStatus(accountId: number, status: AccountStatus): Promise<Driver> {
  return request.post<Driver>(`/api/carrier/drivers/${accountId}/account-status`, {
    account_status: status,
  })
}

/** 读取司机身份与驾驶资格提交历史。 */
export function fetchDriverIdentityHistory(accountId: number): Promise<DriverIdentityRecord[]> {
  return request.get<DriverIdentityRecord[]>(`/api/carrier/drivers/${accountId}/identity-history`)
}
