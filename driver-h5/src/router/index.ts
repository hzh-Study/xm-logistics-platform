import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/login' },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/onboarding',
    name: 'Onboarding',
    component: () => import('@/views/OnboardingView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/blocked',
    name: 'Blocked',
    component: () => import('@/views/BlockedView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/home',
    name: 'DriverHome',
    component: () => import('@/views/HomeView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/tasks',
    name: 'DriverTasks',
    component: () => import('@/views/TasksView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/tasks/:taskId/departure',
    name: 'DriverDeparture',
    component: () => import('@/views/DepartureView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/tasks/:taskId/exception',
    name: 'DriverException',
    component: () => import('@/views/ExceptionView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/tasks/:taskId/signoff',
    name: 'DriverSignoff',
    component: () => import('@/views/SignoffView.vue'),
    meta: { requiresAuth: true },
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) {
    await auth.restore()
  }
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'Login' }
  }
  // 司机端仅允许司机角色进入，其他角色已登录也应退出
  if (to.meta.requiresAuth && auth.role && auth.role !== '司机') {
    return { name: 'Login' }
  }
  if (auth.isLoggedIn && auth.role === '司机') {
    if (auth.blockedReason) {
      return to.name === 'Blocked' ? true : { name: 'Blocked' }
    }
    if (auth.needsOnboarding) {
      return to.name === 'Onboarding' ? true : { name: 'Onboarding' }
    }
    if (to.name === 'Onboarding' || to.name === 'Blocked') {
      return { name: 'DriverHome' }
    }
  }
  if (to.name === 'Login' && auth.isLoggedIn && auth.role === '司机') {
    if (auth.blockedReason) return { name: 'Blocked' }
    return { name: auth.needsOnboarding ? 'Onboarding' : 'DriverHome' }
  }
  return true
})
