import { request } from '@/api/request'
import type {
  Availability,
  DocumentStatus,
  Lifecycle,
  OwnerType,
  Vehicle,
  VehicleCreatePayload,
} from '@/types/vehicle'

export interface VehicleFilters {
  availability?: Availability
  lifecycle?: Lifecycle
  owner_type?: OwnerType
  assignable?: boolean
}

/** 列出本公司车辆，可按两个独立状态与可分配性筛选。 */
export function listVehicles(filters: VehicleFilters = {}): Promise<Vehicle[]> {
  const query = new URLSearchParams()
  if (filters.availability) query.set('availability', filters.availability)
  if (filters.lifecycle) query.set('lifecycle', filters.lifecycle)
  if (filters.owner_type) query.set('owner_type', filters.owner_type)
  if (filters.assignable) query.set('assignable', 'true')
  const suffix = query.toString()
  return request.get<Vehicle[]>(`/api/carrier/vehicles${suffix ? `?${suffix}` : ''}`)
}

/** 登记公司车辆或司机个人车辆。 */
export function createVehicle(payload: VehicleCreatePayload): Promise<Vehicle> {
  return request.post<Vehicle>('/api/carrier/vehicles', payload)
}

/** 读取一辆本公司车辆。 */
export function getVehicle(vehicleId: number): Promise<Vehicle> {
  return request.get<Vehicle>(`/api/carrier/vehicles/${vehicleId}`)
}

/** 把公司名下车辆分配给本公司司机。 */
export function assignVehicle(vehicleId: number, driverAccountId: number): Promise<Vehicle> {
  return request.post<Vehicle>(`/api/carrier/vehicles/${vehicleId}/assign`, {
    driver_account_id: driverAccountId,
  })
}

/** 设置可用性，不影响生命周期。 */
export function setVehicleAvailability(
  vehicleId: number,
  availability: Availability,
): Promise<Vehicle> {
  return request.post<Vehicle>(`/api/carrier/vehicles/${vehicleId}/availability`, {
    availability,
  })
}

/** 设置生命周期，不影响可用性。 */
export function setVehicleLifecycle(
  vehicleId: number,
  lifecycle: Lifecycle,
): Promise<Vehicle> {
  return request.post<Vehicle>(`/api/carrier/vehicles/${vehicleId}/lifecycle`, {
    lifecycle,
  })
}

/** 设置车辆证件状态。 */
export function setVehicleDocumentStatus(
  vehicleId: number,
  documentStatus: DocumentStatus,
): Promise<Vehicle> {
  return request.post<Vehicle>(`/api/carrier/vehicles/${vehicleId}/document-status`, {
    document_status: documentStatus,
  })
}
