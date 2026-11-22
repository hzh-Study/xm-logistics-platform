import { request } from '@/api/request'
import type {
  Certification,
  CertificationInput,
  CertificationView,
  Order,
  RegisterResult,
  ShipperNotification,
} from '@/types/shipper'

/** 货主注册并下发会话。 */
export function registerShipper(phone: string, password: string): Promise<RegisterResult> {
  return request.post<RegisterResult>('/api/shipper/register', { phone, password })
}

/** 提交个人 / 企业认证资料。 */
export function submitCertification(data: CertificationInput): Promise<Certification> {
  return request.post<Certification>('/api/shipper/certification', data)
}

/** 读取认证状态与提交历史。 */
export function fetchCertification(): Promise<CertificationView> {
  return request.get<CertificationView>('/api/shipper/certification')
}

/** 读取货主站内通知。 */
export function fetchNotifications(): Promise<ShipperNotification[]> {
  return request.get<ShipperNotification[]>('/api/shipper/notifications')
}

/** 发布运输订单。 */
export function publishOrder(cargoName: string): Promise<Order> {
  return request.post<Order>('/api/shipper/orders', { cargo_name: cargoName })
}

/** 读取货主自己的运输订单。 */
export function fetchOrders(): Promise<Order[]> {
  return request.get<Order[]>('/api/shipper/orders')
}
