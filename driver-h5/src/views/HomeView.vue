<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

async function onLogout(): Promise<void> {
  await auth.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="driver-home">
    <header class="topbar">
      <span>{{ auth.onboarding?.company_name || '司机' }} · {{ auth.user?.phone }}</span>
      <button class="logout" type="button" @click="onLogout">退出</button>
    </header>
    <main class="body">
      <h1 class="page-title">今日任务</h1>
      <button class="task-entry" type="button" @click="router.push('/tasks')">
        查看我的运输任务（含待确认）
      </button>
    </main>
    <nav class="tabbar">
      <button class="tab active" type="button" @click="router.push('/tasks')">任务</button>
      <button class="tab" type="button">运输记录</button>
      <button class="tab" type="button">费用</button>
    </nav>
  </div>
</template>

<style scoped>
.driver-home {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
}

.logout {
  min-height: var(--tap-min);
  padding: 0 var(--space-3);
  font: inherit;
  color: var(--color-text);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.body {
  flex: 1;
  padding: var(--space-4);
}

.page-title {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.task-entry {
  width: 100%;
  min-height: var(--tap-min);
  padding: var(--space-4);
  font: inherit;
  text-align: left;
  color: var(--color-text);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
}

.tabbar {
  position: sticky;
  bottom: 0;
  display: flex;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  padding-bottom: var(--safe-bottom);
}

.tab {
  flex: 1;
  min-height: var(--tap-min);
  font: inherit;
  color: var(--color-text-muted);
  background: transparent;
  border: 0;
}

.tab.active {
  color: var(--color-accent);
  font-weight: 600;
}
</style>
