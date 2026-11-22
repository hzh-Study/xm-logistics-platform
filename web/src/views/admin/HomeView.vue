<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
</script>

<template>
  <section class="home">
    <h1 class="page-title">工作台</h1>
    <p class="page-note">{{ auth.user?.phone }} · 管理员</p>
    <div class="panel">
      <h2 class="panel-title">认证审核</h2>
      <p class="panel-text">审核物流公司企业认证资料，驳回须填写公司可见的原因。</p>
      <el-link type="primary" @click="router.push('/admin/carriers')">进入物流公司审核</el-link>
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
