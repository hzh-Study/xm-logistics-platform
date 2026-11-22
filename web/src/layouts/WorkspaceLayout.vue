<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { CurrentUser } from '@/types/auth'

const auth = useAuthStore()
const router = useRouter()

const menus = computed(() => menuFor(auth.role))
const roleLabel = computed(() => auth.role ?? '')

function menuFor(role: CurrentUser['role'] | null): { name: string; path: string }[] {
  const all: Record<CurrentUser['role'], { name: string; path: string }[]> = {
    货主: [
      { name: '工作台', path: '/shipper' },
      { name: '货主认证', path: '/shipper/certification' },
      { name: '仓库管理', path: '/shipper/warehouses' },
      { name: '发布运输订单', path: '/shipper/orders/new' },
      { name: '我的订单', path: '/shipper/orders' },
    ],
    物流公司: [
      { name: '工作台', path: '/carrier' },
      { name: '企业认证', path: '/carrier/certification' },
      { name: '订单池', path: '/carrier/order-pool' },
      { name: '派单管理', path: '/carrier/dispatch' },
      { name: '运输异常', path: '/carrier/exceptions' },
      { name: '取消申请处理', path: '/carrier/cancel-applications' },
      { name: '司机管理', path: '/carrier/drivers' },
      { name: '车辆管理', path: '/carrier/vehicles' },
      { name: '费用审核', path: '/carrier/expenses' },
    ],
    管理员: [
      { name: '工作台', path: '/admin' },
      { name: '货主认证审核', path: '/admin/shipper-certifications' },
      { name: '公司认证审核', path: '/admin/carriers' },
      { name: '订单管理', path: '/admin' },
    ],
    司机: [],
  }
  return role ? all[role] : []
}

async function onLogout(): Promise<void> {
  await auth.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="workspace">
    <aside class="sidebar">
      <div class="brand">物流运输管理平台</div>
      <nav class="menu">
        <button
          v-for="item in menus"
          :key="item.name"
          class="menu-item"
          type="button"
          @click="router.push(item.path)"
        >
          {{ item.name }}
        </button>
      </nav>
    </aside>
    <div class="main">
      <header class="topbar">
        <span class="role-badge">{{ roleLabel }}</span>
        <button class="logout" type="button" @click="onLogout">退出登录</button>
      </header>
      <div class="content">
        <RouterView />
      </div>
    </div>
  </div>
</template>

<style scoped>
.workspace {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
}

.brand {
  padding: var(--space-6) var(--space-4);
  font-size: var(--font-size-lg);
  font-weight: 600;
  border-bottom: 1px solid var(--color-border);
}

.menu {
  display: flex;
  flex-direction: column;
  padding: var(--space-2);
}

.menu-item {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font: inherit;
  color: var(--color-text);
  background: transparent;
  border: 0;
  border-radius: var(--radius);
  cursor: pointer;
}

.menu-item:hover {
  background: var(--color-bg);
}

.main {
  flex: 1;
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-4);
  height: 56px;
  padding: 0 var(--space-6);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.role-badge {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.logout {
  font: inherit;
  color: var(--color-text);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--space-1) var(--space-3);
  cursor: pointer;
}

.content {
  max-width: var(--layout-max);
  margin: 0 auto;
  padding: var(--space-6);
}
</style>
