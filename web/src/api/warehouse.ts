import { request } from '@/api/request'
import type { Warehouse, WarehouseInput, WarehouseStatus } from '@/types/warehouse'

/** 列出当前货主的仓库，可按名称与状态筛选。 */
export function fetchWarehouses(
  name?: string,
  status?: WarehouseStatus,
): Promise<Warehouse[]> {
  const params = new URLSearchParams()
  if (name) params.set('name', name)
  if (status) params.set('status', status)
  const query = params.toString()
  return request.get<Warehouse[]>(`/api/shipper/warehouses${query ? `?${query}` : ''}`)
}

/** 新增仓库。 */
export function createWarehouse(data: WarehouseInput): Promise<Warehouse> {
  return request.post<Warehouse>('/api/shipper/warehouses', data)
}

/** 修改仓库主数据。 */
export function updateWarehouse(id: number, data: WarehouseInput): Promise<Warehouse> {
  return request.put<Warehouse>(`/api/shipper/warehouses/${id}`, data)
}

/** 停用仓库，使其不再作为新订单的发货来源。 */
export function disableWarehouse(id: number): Promise<Warehouse> {
  return request.post<Warehouse>(`/api/shipper/warehouses/${id}/disable`)
}

/** 重新启用仓库。 */
export function enableWarehouse(id: number): Promise<Warehouse> {
  return request.post<Warehouse>(`/api/shipper/warehouses/${id}/enable`)
}
