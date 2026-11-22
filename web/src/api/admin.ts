import { request } from '@/api/request'
import type {
  AccountStatusResult,
  AdminStats,
  Announcement,
  CertCategory,
  CertItem,
  CertReview,
  DriverSummary,
  PlatformException,
  PlatformExceptionCategory,
  PlatformExceptionView,
  PlatformHandling,
  PlatformNotice,
  PlatformResult,
  ReviewDecision,
  ShipperSummary,
  VehicleSummary,
  VehicleTransfer,
} from '@/types/admin'
import type {
  CarrierSummary,
  CertificationRecord,
} from '@/types/carrier'
import type { TransportTask } from '@/types/dispatch'
import type { Order } from '@/types/order'
import type { AdminCertification } from '@/types/shipper'

/** 拼接查询串，忽略空值。 */
function queryOf(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

/** 管理员首页运营统计。 */
export function fetchAdminStats(): Promise<AdminStats> {
  return request.get<AdminStats>('/api/admin/stats')
}

/** 全平台货主查询。 */
export function fetchShippers(params: {
  company_name?: string
  auth_status?: string
}): Promise<ShipperSummary[]> {
  return request.get<ShipperSummary[]>(`/api/admin/shippers${queryOf(params)}`)
}

/** 全平台司机查询。 */
export function fetchDrivers(params: {
  driver_name?: string
  auth_status?: string
}): Promise<DriverSummary[]> {
  return request.get<DriverSummary[]>(`/api/admin/drivers${queryOf(params)}`)
}

/** 全平台车辆查询。 */
export function fetchVehicles(params: {
  plate_no?: string
  document_review_status?: string
}): Promise<VehicleSummary[]> {
  return request.get<VehicleSummary[]>(`/api/admin/vehicles${queryOf(params)}`)
}

/** 全平台运输订单查询。 */
export function fetchPlatformOrders(params: {
  order_no?: string
  shipper?: string
  company?: string
  status?: string
  published_from?: string
  published_to?: string
}): Promise<Order[]> {
  return request.get<Order[]>(`/api/admin/orders${queryOf(params)}`)
}

/** 读取全平台任意运输订单详情。 */
export function fetchPlatformOrder(orderId: number): Promise<Order> {
  return request.get<Order>(`/api/admin/orders/${orderId}`)
}

/** 全平台运输任务查询。 */
export function fetchPlatformTasks(params: {
  status?: string
  order_id?: number
  task_no?: string
}): Promise<TransportTask[]> {
  return request.get<TransportTask[]>(`/api/admin/tasks${queryOf(params)}`)
}

/** 读取全平台任意运输任务详情。 */
export function fetchPlatformTask(taskId: number): Promise<TransportTask> {
  return request.get<TransportTask>(`/api/admin/tasks/${taskId}`)
}

/** 五类认证的统一直观列表。 */
export function fetchCertifications(params: {
  category?: CertCategory
  status?: string
}): Promise<CertItem[]> {
  return request.get<CertItem[]>(`/api/admin/certifications${queryOf(params)}`)
}

/** 统一审核；驳回原因必填由服务端强制。 */
export function reviewCertificationUnified(payload: {
  category: CertCategory
  target_id: number
  decision: ReviewDecision
  reason: string
}): Promise<CertReview> {
  return request.post<CertReview>('/api/admin/certifications/review', payload)
}

/** 统一禁用或恢复业务账号。 */
export function setAccountStatus(
  accountId: number,
  accountStatus: '正常使用' | '已禁用',
): Promise<AccountStatusResult> {
  return request.post<AccountStatusResult>(
    `/api/admin/accounts/${accountId}/status`,
    { account_status: accountStatus },
  )
}

/** 发布平台公告。 */
export function publishAnnouncement(payload: {
  title: string
  body: string
  scope: string
}): Promise<Announcement> {
  return request.post<Announcement>('/api/admin/announcements', payload)
}

/** 列出平台公告。 */
export function fetchAnnouncements(): Promise<Announcement[]> {
  return request.get<Announcement[]>('/api/admin/announcements')
}

/** 发布平台通知。 */
export function publishNotice(payload: {
  title: string
  body: string
  scope: string
}): Promise<PlatformNotice> {
  return request.post<PlatformNotice>('/api/admin/notices', payload)
}

/** 列出平台通知。 */
export function fetchNotices(): Promise<PlatformNotice[]> {
  return request.get<PlatformNotice[]>('/api/admin/notices')
}

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
    `/api/admin/carrier-certifications/${accountId}/review`,
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

/** 按类别列出平台异常登记记录。 */
export function fetchPlatformExceptions(
  category?: PlatformExceptionCategory,
): Promise<PlatformException[]> {
  return request.get<PlatformException[]>(
    `/api/admin/platform-exceptions${queryOf(category ? { category } : {})}`,
  )
}

/** 管理员登记平台异常。 */
export function createPlatformException(payload: {
  category: PlatformExceptionCategory
  subject: string
  detail: string
  subject_account_id?: number
  order_id?: number
  task_id?: number
  vehicle_id?: number
}): Promise<PlatformException> {
  return request.post<PlatformException>('/api/admin/platform-exceptions', payload)
}

/** 读取平台异常及全部追加处理记录。 */
export function fetchPlatformException(id: number): Promise<PlatformExceptionView> {
  return request.get<PlatformExceptionView>(`/api/admin/platform-exceptions/${id}`)
}

/** 管理员追加异常处理记录。 */
export function appendPlatformHandling(
  exceptionId: number,
  payload: { result: PlatformResult; reason: string; detail?: string },
): Promise<PlatformHandling> {
  return request.post<PlatformHandling>(
    `/api/admin/platform-exceptions/${exceptionId}/handling`,
    payload,
  )
}

/** 列出车辆转籍历史，可按车辆筛选。 */
export function fetchVehicleTransfers(vehicleId?: number): Promise<VehicleTransfer[]> {
  return request.get<VehicleTransfer[]>(
    `/api/admin/vehicle-transfers${queryOf(vehicleId ? { vehicle_id: vehicleId } : {})}`,
  )
}

/** 执行车辆转籍（无进行中任务时放行）。 */
export function transferVehicle(payload: {
  vehicle_id: number
  to_carrier_id: number
  reason: string
}): Promise<VehicleTransfer> {
  return request.post<VehicleTransfer>('/api/admin/vehicle-transfers', payload)
}

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
