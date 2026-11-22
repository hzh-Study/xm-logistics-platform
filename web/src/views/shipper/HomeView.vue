<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as shipperApi from '@/api/shipper'
import { useAuthStore } from '@/stores/auth'
import type { Order } from '@/types/shipper'

const auth = useAuthStore()
const router = useRouter()
const cargoName = ref('')
const orders = ref<Order[]>([])
const publishing = ref(false)

async function loadOrders(): Promise<void> {
  try {
    orders.value = await shipperApi.fetchOrders()
  } catch {
    orders.value = []
  }
}

async function onPublish(): Promise<void> {
  if (!cargoName.value.trim()) {
    ElMessage.warning('请填写货物名称')
    return
  }
  publishing.value = true
  try {
    const order = await shipperApi.publishOrder(cargoName.value.trim())
    ElMessage.success(`发布成功，订单号 ${order.order_no}`)
    cargoName.value = ''
    await loadOrders()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '发布失败')
  } finally {
    publishing.value = false
  }
}

onMounted(loadOrders)
</script>

<template>
  <section class="home">
    <h1 class="page-title">工作台</h1>
    <p class="page-note">{{ auth.user?.phone }} · 货主 · 认证状态：{{ auth.user?.auth_status }}</p>

    <div class="panel">
      <h2 class="panel-title">货主认证</h2>
      <p class="panel-text">
        {{
          auth.user?.auth_status === '审核通过'
            ? '认证已通过，可发布运输订单。'
            : '认证未达审核通过，发布运输订单将被阻断。请先提交认证资料。'
        }}
      </p>
      <el-button type="primary" link @click="router.push('/shipper/certification')">
        前往认证资料
      </el-button>
    </div>

    <div class="panel">
      <h2 class="panel-title">发布运输订单</h2>
      <form class="publish-form" @submit.prevent="onPublish">
        <el-input v-model="cargoName" placeholder="请输入货物名称" />
        <el-button type="primary" native-type="submit" :loading="publishing">发布</el-button>
      </form>
      <p v-if="orders.length" class="panel-text">已发布 {{ orders.length }} 条运输订单。</p>
      <p v-else class="panel-text">暂无运输订单。</p>
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
  margin-bottom: var(--space-4);
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
  margin: 0 0 var(--space-3);
  color: var(--color-text-muted);
}

.publish-form {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
</style>
