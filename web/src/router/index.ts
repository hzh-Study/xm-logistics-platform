import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { CurrentUser } from '@/types/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    roles?: CurrentUser['role'][]
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
    path: '/shipper',
    name: 'ShipperWorkspace',
    component: () => import('@/layouts/WorkspaceLayout.vue'),
    meta: { requiresAuth: true, roles: ['货主'] },
    children: [
      { path: '', name: 'ShipperHome', component: () => import('@/views/shipper/HomeView.vue') },
      {
        path: 'certification',
        name: 'ShipperCertification',
        component: () => import('@/views/shipper/CertificationView.vue'),
      },
      {
        path: 'warehouses',
        name: 'ShipperWarehouses',
        component: () => import('@/views/shipper/WarehouseView.vue'),
      },
      {
        path: 'orders',
        name: 'ShipperOrders',
        component: () => import('@/views/shipper/OrderListView.vue'),
      },
      {
        path: 'orders/new',
        name: 'ShipperOrderPublish',
        component: () => import('@/views/shipper/OrderPublishView.vue'),
      },
      {
        path: 'orders/:orderId/progress',
        name: 'ShipperOrderProgress',
        component: () => import('@/views/shipper/OrderProgressView.vue'),
      },
      {
        path: 'orders/:orderId/cancel',
        name: 'ShipperOrderCancel',
        component: () => import('@/views/shipper/OrderCancelView.vue'),
      },
    ],
  },
  {
    path: '/carrier',
    name: 'CarrierWorkspace',
    component: () => import('@/layouts/WorkspaceLayout.vue'),
    meta: { requiresAuth: true, roles: ['物流公司'] },
    children: [
      { path: '', name: 'CarrierHome', component: () => import('@/views/carrier/HomeView.vue') },
      {
        path: 'certification',
        name: 'CarrierCertification',
        component: () => import('@/views/carrier/CertificationView.vue'),
      },
      {
        path: 'order-pool',
        name: 'CarrierOrderPool',
        component: () => import('@/views/carrier/OrderPoolView.vue'),
      },
      {
        path: 'dispatch',
        name: 'CarrierDispatch',
        component: () => import('@/views/carrier/DispatchView.vue'),
      },
      {
        path: 'tasks/:taskId/progress',
        name: 'CarrierTaskProgress',
        component: () => import('@/views/carrier/TaskProgressView.vue'),
      },
      {
        path: 'exceptions',
        name: 'CarrierExceptions',
        component: () => import('@/views/carrier/ExceptionTasksView.vue'),
      },
      {
        path: 'cancel-applications',
        name: 'CarrierCancelApplications',
        component: () => import('@/views/carrier/CancelApplicationsView.vue'),
      },
      {
        path: 'tasks/:taskId/exceptions',
        name: 'CarrierExceptionHandling',
        component: () => import('@/views/carrier/ExceptionHandlingView.vue'),
      },
      {
        path: 'drivers',
        name: 'CarrierDrivers',
        component: () => import('@/views/carrier/DriversView.vue'),
      },
      {
        path: 'vehicles',
        name: 'CarrierVehicles',
        component: () => import('@/views/carrier/VehiclesView.vue'),
      },
      {
        path: 'expenses',
        name: 'CarrierExpenses',
        component: () => import('@/views/carrier/ExpensesView.vue'),
      },
    ],
  },
  {
    path: '/admin',
    name: 'AdminWorkspace',
    component: () => import('@/layouts/WorkspaceLayout.vue'),
    meta: { requiresAuth: true, roles: ['管理员'] },
    children: [
      { path: '', name: 'AdminHome', component: () => import('@/views/admin/HomeView.vue') },
      {
        path: 'shipper-certifications',
        name: 'AdminShipperCertifications',
        component: () => import('@/views/admin/ShipperCertificationsView.vue'),
      },
      {
        path: 'carriers',
        name: 'AdminCarrierReview',
        component: () => import('@/views/admin/CarrierReviewView.vue'),
      },
    ],
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
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.roles && auth.role && !to.meta.roles.includes(auth.role)) {
    return { name: 'Login' }
  }
  return true
})
