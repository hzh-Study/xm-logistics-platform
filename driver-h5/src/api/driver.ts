import { request } from '@/api/request'
import type { DriverBindingPayload, DriverSelf, Onboarding } from '@/types/driver'

/** 读取首次登录强制改密与身份绑定的当前状态。 */
export function fetchOnboarding(): Promise<Onboarding> {
  return request.get<Onboarding>('/api/driver/onboarding')
}

/** 修改初始密码并解除强制改密。 */
export function changePassword(newPassword: string): Promise<void> {
  return request.post<void>('/api/driver/change-password', { new_password: newPassword })
}

/** 补全身份与驾驶资格资料完成身份绑定。 */
export function completeBinding(payload: DriverBindingPayload): Promise<DriverSelf> {
  return request.post<DriverSelf>('/api/driver/binding', payload)
}

/** 读取司机工作台自身资料（已通过门禁）。 */
export function fetchDriverWorkspace(): Promise<DriverSelf> {
  return request.get<DriverSelf>('/api/driver/workspace')
}
