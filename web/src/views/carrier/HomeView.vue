<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCapabilities, fetchCertification } from '@/api/carrier'
import { listCarrierOrders, listTasks } from '@/api/dispatch'
import { listExpenses } from '@/api/expense'
import { listDrivers } from '@/api/driver'
import { listVehicles } from '@/api/vehicle'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { Capabilities, CertificationView } from '@/types/carrier'
import type { Order } from '@/types/order'
import type { TransportTask } from '@/types/dispatch'
import type { Expense } from '@/types/expense'
import type { Driver } from '@/types/driver'
import type { Vehicle } from '@/types/vehicle'

const auth = useAuthStore()
const router = useRouter()
const certification = ref<CertificationView | null>(null)
const capabilities = ref<Capabilities | null>(null)
const orders = ref<Order[]>([])
const tasks = ref<TransportTask[]>([])
const expenses = ref<Expense[]>([])
const drivers = ref<Driver[]>([])
const vehicles = ref<Vehicle[]>([])
const loading = ref(false)

const today = new Date().toISOString().slice(0, 10)

const stats = computed(() => {
  const count = (status: string) => tasks.value.filter((task) => task.status === status).length
  return [
    { label: '企业认证状态', value: certification.value?.auth_status ?? '—' },
    { label: '今日承接', value: orders.value.filter((order) => (order.accepted_at ?? '').slice(0, 10) === today).length },
    { label: '待派单', value: orders.value.filter((order) => order.status === '已承接').length },
    { label: '待司机确认', value: count('待司机确认') },
    { label: '运输中', value: count('运输中') },
    { label: '已完成', value: count('已完成') },
    { label: '异常', value: count('异常') },
    { label: '待审费用', value: expenses.value.filter((expense) => expense.review_status === '待审核').length },
    { label: '司机数', value: drivers.value.length },
    { label: '车辆数', value: vehicles.value.length },
  ]
})

const todos = computed(() => [
  { text: `派单管理 · ${stats.value[2].value} 条运输订单待派单`, path: '/carrier/dispatch', action: '去处理' },
  { text: `任务确认 · ${stats.value[3].value} 条派单待司机确认`, path: '/carrier/dispatch', action: '去查看' },
  { text: `费用审核 · ${stats.value[7].value} 笔报销费用待审核`, path: '/carrier/expenses', action: '去审核' },
  { text: `运输异常 · ${stats.value[6].value} 条异常待处置`, path: '/carrier/exceptions', action: '去处置' },
])

const recentTasks = computed(() => tasks.value.slice(0, 5))

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const results = await Promise.allSettled([
      fetchCertification(),
      fetchCapabilities(),
      listCarrierOrders(),
      listTasks(),
      listExpenses({ review_status: '待审核' }),
      listDrivers(),
      listVehicles(),
    ])
    if (results[0].status === 'fulfilled') certification.value = results[0].value
    if (results[1].status === 'fulfilled') capabilities.value = results[1].value
    if (results[2].status === 'fulfilled') orders.value = results[2].value
    if (results[3].status === 'fulfilled') tasks.value = results[3].value
    if (results[4].status === 'fulfilled') expenses.value = results[4].value
    if (results[5].status === 'fulfilled') drivers.value = results[5].value
    if (results[6].status === 'fulfilled') vehicles.value = results[6].value
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="工作台" :subtitle="`${auth.user?.phone ?? ''} · 物流公司 · ${certification?.auth_status ?? ''}`" />

    <div class="stats-grid">
      <StatCard v-for="item in stats" :key="item.label" :value="item.value" :label="item.label" />
    </div>

    <div class="panel-gap" />

    <NoticeBar v-if="capabilities?.reasons.length" tone="warning">
      承运业务暂不可用：{{ capabilities.reasons.join('；') }}。<router-link to="/carrier/certification" class="link">前往企业认证</router-link>
    </NoticeBar>
    <NoticeBar v-else tone="info">
      企业认证：<StatusPill :text="certification?.auth_status ?? '未提交'" /> · 账号状态：<StatusPill :text="auth.user?.account_status ?? '正常使用'" />。承接与派单功能可用。
    </NoticeBar>

    <div class="panel-gap" />

    <section class="panel">
      <div class="panel-head"><span class="panel-title">待办事项</span></div>
      <div class="panel-body">
        <ul class="list-simple">
          <li v-for="item in todos" :key="item.text">
            <span>{{ item.text }}</span>
            <span class="meta"><router-link :to="item.path" class="link">{{ item.action }}</router-link></span>
          </li>
        </ul>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">最近运输动态</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!recentTasks.length" text="暂无运输任务" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">任务编号</th><th>货物 / 订单</th><th>司机 / 车辆</th><th>任务状态</th><th class="num">更新时间</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="task in recentTasks" :key="task.id">
                <td class="num">{{ task.task_no }}</td>
                <td>{{ task.order_no }}<div class="cell-sub">{{ task.notes || '—' }}</div></td>
                <td>{{ task.driver_name }} / {{ task.vehicle_plate }}</td>
                <td><StatusPill :text="task.status" /></td>
                <td class="num">{{ stamp(task.created_at) }}</td>
                <td class="ops">
                  <el-button type="primary" link @click="router.push(`/carrier/tasks/${task.id}/progress`)">查看进度</el-button>
                </td>
              </tr>
            </tbody>
          </table>
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
