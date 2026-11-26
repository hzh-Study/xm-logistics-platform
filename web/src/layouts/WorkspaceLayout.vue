<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { CurrentUser } from '@/types/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const navOpen = ref(false)

const menus = computed(() => menuFor(auth.role))
const roleLabel = computed(() => auth.role ?? '')

const ICONS: Record<string, string> = {
  dashboard: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  cert: 'M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5l-8-3ZM9 12l2 2 4-4',
  warehouse: 'm12 2 9 5-9 5-9-5 9-5ZM3 7v10l9 5 9-5V7M12 12v10',
  plus: 'M12 5v14M5 12h14',
  list: 'M6 2h8l5 5v15H6zM14 2v5h5M9 12h7M9 16h7',
  pool: 'M5 5h14l2 7v7H3v-7l2-7ZM3 12h5l2 3h4l2-3h5',
  dispatch: 'M4 8h13l-3-3M20 16H7l3 3',
  warn: 'M12 3 2 21h20L12 3ZM12 9v5M12 17h.01',
  cancel: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18ZM5 5l14 14',
  driver: 'M9 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2 20c0-3.3 3-5 7-5s7 1.7 7 5M17 8a3 3 0 0 1 0 6M18 15c2.4.6 4 2.2 4 5',
  vehicle: 'M2 6h11v11H2zM13 10h4l4 4v3h-8zM6 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM17 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
  expense: 'M4 4h16v16H4zM8 9h8M8 13h8M8 17h4',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14ZM20 20l-4-4',
  notice: 'M4 5h16v14H4zM8 9h8M8 13h5',
  transfer: 'M4 8h13l-3-3M20 16H7l3 3',
  shield: 'M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5l-8-3Z',
}

interface MenuItem { name: string; path: string; icon: string }

function menuFor(role: CurrentUser['role'] | null): MenuItem[] {
  const all: Record<CurrentUser['role'], MenuItem[]> = {
    货主: [
      { name: '工作台', path: '/shipper', icon: 'dashboard' },
      { name: '货主认证', path: '/shipper/certification', icon: 'cert' },
      { name: '仓库管理', path: '/shipper/warehouses', icon: 'warehouse' },
      { name: '发布运输订单', path: '/shipper/orders/new', icon: 'plus' },
      { name: '我的订单', path: '/shipper/orders', icon: 'list' },
    ],
    物流公司: [
      { name: '工作台', path: '/carrier', icon: 'dashboard' },
      { name: '企业认证', path: '/carrier/certification', icon: 'cert' },
      { name: '订单池', path: '/carrier/order-pool', icon: 'pool' },
      { name: '派单管理', path: '/carrier/dispatch', icon: 'dispatch' },
      { name: '运输异常', path: '/carrier/exceptions', icon: 'warn' },
      { name: '取消申请处理', path: '/carrier/cancel-applications', icon: 'cancel' },
      { name: '司机管理', path: '/carrier/drivers', icon: 'driver' },
      { name: '车辆管理', path: '/carrier/vehicles', icon: 'vehicle' },
      { name: '费用审核', path: '/carrier/expenses', icon: 'expense' },
    ],
    管理员: [
      { name: '工作台', path: '/admin', icon: 'dashboard' },
      { name: '统一认证审核', path: '/admin/certifications', icon: 'shield' },
      { name: '平台主体查询', path: '/admin/accounts', icon: 'search' },
      { name: '运输订单查询', path: '/admin/orders', icon: 'list' },
      { name: '运输任务查询', path: '/admin/tasks', icon: 'vehicle' },
      { name: '平台公告与通知', path: '/admin/announcements', icon: 'notice' },
      { name: '平台异常管理', path: '/admin/platform-exceptions', icon: 'warn' },
      { name: '车辆转籍', path: '/admin/vehicle-transfers', icon: 'transfer' },
      { name: '货主认证审核', path: '/admin/shipper-certifications', icon: 'cert' },
      { name: '公司认证审核', path: '/admin/carriers', icon: 'cert' },
    ],
    司机: [],
  }
  return role ? all[role] : []
}

const currentTitle = computed(() => {
  const path = route.path
  const matched = menus.value
    .filter((item) => item.path === path || (item.path !== '/shipper' && item.path !== '/carrier' && item.path !== '/admin' && path.startsWith(`${item.path}/`)))
    .sort((a, b) => b.path.length - a.path.length)
  return matched[0]?.name ?? '工作台'
})

const isActive = (path: string): boolean => {
  if (path === '/shipper' || path === '/carrier' || path === '/admin') return route.path === path
  return route.path === path || route.path.startsWith(`${path}/`)
}

async function onLogout(): Promise<void> {
  await auth.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="workspace">
    <aside class="sidebar" :class="{ 'sidebar--open': navOpen }">
      <div class="brand">
        <span class="brand__mark">运</span>
        <span>物流运输管理<span class="brand__sub">平台</span></span>
      </div>
      <nav class="nav">
        <button
          v-for="item in menus"
          :key="item.path"
          class="nav-item"
          :class="{ 'nav-item--active': isActive(item.path) }"
          type="button"
          @click="router.push(item.path); navOpen = false"
        >
          <svg class="nav-item__icon" viewBox="0 0 24 24" aria-hidden="true">
            <path :d="ICONS[item.icon]" />
          </svg>
          <span>{{ item.name }}</span>
        </button>
      </nav>
    </aside>
    <div class="main">
      <header class="topbar">
        <button class="topbar__menu" type="button" aria-label="展开菜单" @click="navOpen = !navOpen">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
        </button>
        <div class="crumb">{{ roleLabel }} <span>/</span> <b>{{ currentTitle }}</b></div>
        <div class="topbar__right">
          <span class="topbar__user">{{ auth.user?.phone }}</span>
          <span class="role-tag">{{ roleLabel }}</span>
          <button class="logout" type="button" @click="onLogout">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 4H5v16h5M14 8l4 4-4 4M18 12H9" /></svg>
            退出
          </button>
        </div>
      </header>
      <div class="content"><RouterView /></div>
    </div>
  </div>
</template>

<style scoped>
.workspace { display: grid; grid-template-columns: var(--sidebar-width) minmax(0, 1fr); min-height: 100vh; }
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 56px;
  padding: 0 var(--space-5);
  border-bottom: 1px solid var(--color-border);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.2px;
  flex: 0 0 auto;
}
.brand__mark {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-control);
  background: var(--color-accent);
  color: var(--color-surface);
  font-size: var(--font-size-sm);
  font-weight: 600;
}
.brand__sub { font-size: var(--font-size-xs); color: var(--color-text-3); font-weight: 400; }
.nav { flex: 1; padding: var(--space-3) var(--space-3) var(--space-6); }
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  height: 36px;
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-2);
  font-size: var(--font-size-md);
  text-align: left;
  cursor: pointer;
}
.nav-item:hover { background: var(--color-fill); color: var(--color-text); }
.nav-item--active { background: var(--color-accent-soft); color: var(--color-accent); font-weight: 500; }
.nav-item__icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.main { min-width: 0; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: var(--space-4);
  height: 56px;
  padding: 0 var(--space-8);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}
.topbar__menu { display: none; border: 0; background: transparent; cursor: pointer; }
.topbar__menu svg { width: 20px; height: 20px; fill: none; stroke: var(--color-text-2); stroke-width: 1.5; }
.crumb { font-size: var(--font-size-sm); color: var(--color-text-3); }
.crumb span { color: var(--color-border-strong); margin: 0 var(--space-2); }
.crumb b { color: var(--color-text-2); font-weight: 500; }
.topbar__right { display: flex; align-items: center; gap: var(--space-4); margin-left: auto; }
.topbar__user { font-size: var(--font-size-sm); color: var(--color-text-2); }
.role-tag {
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  background: var(--color-accent-soft);
  color: var(--color-accent);
  font-size: var(--font-size-xs);
  font-weight: 500;
}
.logout {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  border: 0;
  background: transparent;
  color: var(--color-text-2);
  font-size: var(--font-size-sm);
  cursor: pointer;
  padding: var(--space-2);
  border-radius: var(--radius-control);
}
.logout:hover { color: var(--color-accent); background: var(--color-accent-soft); }
.logout svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
.content { max-width: var(--layout-max); margin: 0 auto; padding: var(--space-6) var(--space-8) var(--space-12); }

@media (max-width: 900px) {
  .workspace { grid-template-columns: minmax(0, 1fr); }
  .sidebar { display: none; position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--color-border); }
  .sidebar--open { display: block; }
  .topbar { padding: 0 var(--space-4); }
  .topbar__menu { display: grid; place-items: center; }
  .topbar__user { display: none; }
  .content { padding: var(--space-5) var(--space-4) var(--space-10); }
}
</style>
