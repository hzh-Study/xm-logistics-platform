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
  <main class="blocked-page">
    <h1 class="blocked-title">暂不可使用司机端</h1>
    <p class="blocked-reason">{{ auth.blockedReason || '当前账号不满足业务条件。' }}</p>
    <p class="blocked-note">请联系所属物流公司或平台处理，历史运输记录不受影响。</p>
    <van-button class="logout" type="primary" block @click="onLogout">退出登录</van-button>
  </main>
</template>

<style scoped>
.blocked-page {
  padding: var(--space-6) var(--space-4);
}

.blocked-title {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.blocked-reason {
  padding: var(--space-4);
  color: var(--color-error);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.blocked-note {
  margin: var(--space-4) 0 var(--space-6);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.logout {
  min-height: var(--tap-min);
}
</style>
