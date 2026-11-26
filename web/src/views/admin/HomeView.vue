<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { AdminStats } from '@/types/admin'
import type { Order } from '@/types/order'

const stats = ref<AdminStats | null>(null)
const orders = ref<Order[]>([])
const loading = ref(false)

const cards = computed(() => {
  const s = stats.value
  return [
    { label: '货主数', value: s?.shipper_count ?? '—' },
    { label: '公司数', value: s?.carrier_count ?? '—' },
    { label: '司机数', value: s?.driver_count ?? '—' },
    { label: '车辆数', value: s?.vehicle_count ?? '—' },
    { label: '订单总数', value: orders.value.length || '—' },
    { label: '待承接', value: s?.orders_pending_accept ?? '—' },
    { label: '运输中', value: s?.orders_in_transit ?? '—' },
    { label: '已完成', value: s?.orders_completed ?? '—' },
    { label: '异常', value: s?.orders_exception ?? '—' },
    { label: '待审认证', value: s?.pending_certifications ?? '—' },
  ]
})

const todos = [
  { text: '统一认证审核', path: '/admin/certifications', action: '去审核' },
  { text: '货主认证审核', path: '/admin/shipper-certifications', action: '去审核' },
  { text: '公司认证审核', path: '/admin/carriers', action: '去审核' },
  { text: '车辆转籍', path: '/admin/vehicle-transfers', action: '去处理' },
  { text: '平台异常管理', path: '/admin/platform-exceptions', action: '去处置' },
]

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

onMounted(async () => {
  loading.value = true
  try {
    const [adminStats, orderRows] = await Promise.all([
      adminApi.fetchAdminStats(),
      adminApi.fetchPlatformOrders({}),
    ])
    stats.value = adminStats
    orders.value = orderRows
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载运营统计失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="工作台" subtitle="平台管理员 · 全局监控与审核" />

    <div class="stats-grid">
      <StatCard v-for="item in cards" :key="item.label" :value="item.value" :label="item.label" />
    </div>

    <div class="panel-gap" />

    <NoticeBar tone="info">
      管理员仅有平台级只读查询 + 审核 / 禁用恢复 / 公告 / 异常处置权限，不能直接改写订单、运输任务、打卡或费用记录。
    </NoticeBar>

    <div class="panel-gap" />

    <section class="panel">
      <div class="panel-head"><span class="panel-title">审核待办</span></div>
      <div class="panel-body">
        <ul class="list-simple">
          <li v-for="item in todos" :key="item.path">
            <span>{{ item.text }}</span>
            <span class="meta"><router-link :to="item.path" class="link">{{ item.action }}</router-link></span>
          </li>
        </ul>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">平台运输动态</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!orders.length" text="暂无运输订单" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">订单编号</th><th>货主 / 物流公司</th><th>货物</th><th>订单状态</th><th class="num">更新时间</th></tr>
            </thead>
            <tbody>
              <tr v-for="order in orders.slice(0, 8)" :key="order.id">
                <td class="num">{{ order.order_no }}</td>
                <td>货主 #{{ order.shipper_id }} / {{ order.carrier_id ? `公司 #${order.carrier_id}` : '—' }}</td>
                <td>{{ [order.cargo_name, order.quantity].filter(Boolean).join(' · ') }}</td>
                <td><StatusPill :text="order.status" /></td>
                <td class="num">{{ stamp(order.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ orders.length }} 条</span></div>
        </div>
      </div>
    </section>
  </section>
</template>

<style scoped>
.panel-gap { height: var(--space-4); }
.link { color: var(--color-accent); }
.link:hover { color: var(--color-accent-hover); }
</style>
