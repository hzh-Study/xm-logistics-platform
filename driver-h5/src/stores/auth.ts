import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authApi from '@/api/auth'
import * as driverApi from '@/api/driver'
import { request } from '@/api/request'
import type { Onboarding } from '@/types/driver'
import type { CurrentUser } from '@/types/auth'

/** 登录态、当前用户、角色与司机首次登录状态，权限判定的单一来源。 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)
  const onboarding = ref<Onboarding | null>(null)
  const ready = ref(false)

  const isLoggedIn = computed(() => user.value !== null)
  const role = computed(() => user.value?.role ?? null)
  const needsOnboarding = computed(
    () =>
      onboarding.value === null ||
      onboarding.value.must_change_password ||
      !onboarding.value.binding_complete,
  )
  const blockedReason = computed(() => {
    const reason = onboarding.value?.blocked_reason ?? ''
    const flowReasons = ['请先修改初始密码', '请先完成身份绑定']
    return reason && !flowReasons.includes(reason) ? reason : ''
  })

  /** 刷新司机首次登录状态。 */
  async function refreshOnboarding(): Promise<void> {
    try {
      onboarding.value = await driverApi.fetchOnboarding()
    } catch {
      onboarding.value = null
    }
  }

  /** 从服务端恢复会话并取回 CSRF。 */
  async function restore(): Promise<void> {
    try {
      const me = await authApi.fetchMe()
      user.value = me
      request.setCsrfToken(me.csrf_token)
      if (me.role === '司机') {
        await refreshOnboarding()
      } else {
        onboarding.value = null
      }
    } catch {
      user.value = null
      onboarding.value = null
      request.clearCsrfToken()
    } finally {
      ready.value = true
    }
  }

  /** 登录并记住 CSRF token。 */
  async function login(phone: string, password: string): Promise<void> {
    const result = await authApi.login(phone, password)
    user.value = result.user
    request.setCsrfToken(result.csrf_token)
    if (result.user.role === '司机') {
      await refreshOnboarding()
    }
  }

  /** 退出并清除本地登录态。 */
  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      user.value = null
      onboarding.value = null
      request.clearCsrfToken()
    }
  }

  return {
    user,
    onboarding,
    ready,
    isLoggedIn,
    role,
    needsOnboarding,
    blockedReason,
    restore,
    refreshOnboarding,
    login,
    logout,
  }
})
