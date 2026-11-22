import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authApi from '@/api/auth'
import { request } from '@/api/request'
import type { CurrentUser } from '@/types/auth'

/** 登录态、当前用户与角色，权限判定的单一来源。 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)
  const ready = ref(false)

  const isLoggedIn = computed(() => user.value !== null)
  const role = computed(() => user.value?.role ?? null)

  /** 从服务端恢复会话并取回 CSRF。 */
  async function restore(): Promise<void> {
    try {
      const me = await authApi.fetchMe()
      user.value = me
      request.setCsrfToken(me.csrf_token)
    } catch {
      user.value = null
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
  }

  /** 退出并清除本地登录态。 */
  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      user.value = null
      request.clearCsrfToken()
    }
  }

  return { user, ready, isLoggedIn, role, restore, login, logout }
})
