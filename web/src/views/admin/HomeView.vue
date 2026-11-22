<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <section class="home">
    <h1 class="page-title">工作台</h1>
    <p class="page-note">{{ auth.user?.phone }} · 管理员</p>
    <div class="panel">
      <h2 class="panel-title">业务概览</h2>
      <p class="panel-text">仓库管理、运输订单发布与订单跟踪将在后续版本接入。当前账号与权限已可用。</p>
    </div>
  </section>
</template>

<style scoped>
.home {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.page-note {
  margin: var(--space-1) 0 var(--space-6);
  color: var(--color-text-muted);
}

.panel {
  padding: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.panel-title {
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.panel-text {
  margin: 0;
  color: var(--color-text-muted);
}
</style>
