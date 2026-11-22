<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import type { AdminStats } from '@/types/admin'

const router = useRouter()
const stats = ref<AdminStats | null>(null)

onMounted(async () => {
  try {
    stats.value = await adminApi.fetchAdminStats()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载运营统计失败')
  }
})
</script>

<template>
  <section class="home">
    <h1 class="page-title">运营工作台</h1>

    <h2 class="section-title">平台主体</h2>
    <div class="cards">
      <div class="card">
        <span class="card-label">货主</span>
        <span class="card-value">{{ stats?.shipper_count ?? '—' }}</span>
      </div>
      <div class="card">
        <span class="card-label">物流公司</span>
        <span class="card-value">{{ stats?.carrier_count ?? '—' }}</span>
      </div>
      <div class="card">
        <span class="card-label">司机</span>
        <span class="card-value">{{ stats?.driver_count ?? '—' }}</span>
      </div>
      <div class="card">
        <span class="card-label">车辆</span>
        <span class="card-value">{{ stats?.vehicle_count ?? '—' }}</span>
      </div>
    </div>

    <h2 class="section-title">运输订单</h2>
    <div class="cards">
      <div class="card">
        <span class="card-label">待承接</span>
        <span class="card-value">{{ stats?.orders_pending_accept ?? '—' }}</span>
      </div>
      <div class="card">
        <span class="card-label">运输中</span>
        <span class="card-value">{{ stats?.orders_in_transit ?? '—' }}</span>
      </div>
      <div class="card">
        <span class="card-label">已完成</span>
        <span class="card-value">{{ stats?.orders_completed ?? '—' }}</span>
      </div>
      <div class="card">
        <span class="card-label">异常处理中</span>
        <span class="card-value">{{ stats?.orders_exception ?? '—' }}</span>
      </div>
    </div>

    <div class="notice-line">
      <span>待审核认证：{{ stats?.pending_certifications ?? '—' }} 项</span>
      <el-button type="primary" link @click="router.push('/admin/certifications')">
        前往统一审核
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.home {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0 0 var(--space-6);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.section-title {
  margin: var(--space-6) 0 var(--space-3);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-3);
}

.card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.card-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.card-value {
  font-size: var(--font-size-xl);
  font-weight: 600;
}

.notice-line {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-6);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
</style>
