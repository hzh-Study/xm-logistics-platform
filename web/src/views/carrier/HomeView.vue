<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCapabilities, fetchCertification } from '@/api/carrier'
import { useAuthStore } from '@/stores/auth'
import type { Capabilities, CertificationView } from '@/types/carrier'

const auth = useAuthStore()
const router = useRouter()
const certification = ref<CertificationView | null>(null)
const capabilities = ref<Capabilities | null>(null)

onMounted(async () => {
  certification.value = await fetchCertification()
  try {
    capabilities.value = await fetchCapabilities()
  } catch {
    capabilities.value = null
  }
})
</script>

<template>
  <section class="home">
    <h1 class="page-title">工作台</h1>
    <p class="page-note">{{ auth.user?.phone }} · 物流公司</p>

    <div v-if="capabilities?.reasons.length" class="banner">
      <span>承运业务暂不可用：{{ capabilities.reasons.join('；') }}</span>
      <el-link type="primary" @click="router.push('/carrier/certification')">
        去提交企业认证
      </el-link>
    </div>

    <div class="panel">
      <h2 class="panel-title">企业认证</h2>
      <p class="panel-text">当前认证状态：{{ certification?.auth_status ?? '读取中' }}</p>
      <p v-if="certification?.latest?.decision === '审核不通过'" class="reason">
        驳回原因：{{ certification.latest.reason }}
      </p>
      <p class="panel-text">审核通过后，订单池承接、派单、司机管理与车辆管理方可使用。</p>
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

.banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
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

.panel-text,
.reason {
  margin: 0 0 var(--space-2);
  color: var(--color-text-muted);
}
</style>
