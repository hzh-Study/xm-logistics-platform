<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as shipperApi from '@/api/shipper'
import * as warehouseApi from '@/api/warehouse'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { Order } from '@/types/order'
import type { ShipperNotification } from '@/types/shipper'
import type { Warehouse } from '@/types/warehouse'

const auth = useAuthStore()
const router = useRouter()
const orders = ref<Order[]>([])
const warehouses = ref<Warehouse[]>([])
const notices = ref<ShipperNotification[]>([])
const loading = ref(false)
const failed = ref(false)

const stats = computed(() => {
  const all = orders.value
  const count = (status: string) => all.filter((item) => item.status === status).length
  return [
    { label: '仓库数', value: warehouses.value.length },
    { label: '订单总数', value: all.length },
    { label: '待承接', value: count('待承接') },
    { label: '已承接', value: count('已承接') },
    { label: '运输中', value: count('运输中') },
    { label: '已完成', value: count('已完成') },
    { label: '已取消', value: count('已取消') },
  ]
})

const recentOrders = computed(() => orders.value.slice(0, 5))

function shortPlace(snapshot: { province: string; city: string }): string {
  return `${snapshot.province}${snapshot.city}`
}

function shortCargo(order: Order): string {
  return [order.cargo_name, order.weight, order.quantity].filter(Boolean).join(' · ')
}

function time(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const [orderList, warehouseList, noticeList] = await Promise.all([
      shipperApi.fetchOrders(),
      warehouseApi.fetchWarehouses(),
      shipperApi.fetchNotifications(),
    ])
    orders.value = orderList
    warehouses.value = warehouseList
    notices.value = noticeList
  } catch (error) {
    failed.value = true
    ElMessage.error(error instanceof Error ? error.message : '加载工作台数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="工作台" :subtitle="`${auth.user?.phone ?? ''} · 货主 · ${auth.user?.auth_status ?? ''}`" />

    <NoticeBar v-if="failed" tone="error">工作台数据加载失败，请刷新页面重试。</NoticeBar>

    <div class="stats-grid">
      <StatCard v-for="item in stats" :key="item.label" :value="item.value" :label="item.label" />
    </div>

    <div class="panel-gap" />

    <NoticeBar v-if="auth.user?.auth_status === '审核通过'" tone="info">
      当前认证状态：<StatusPill :text="auth.user.auth_status" />。认证已通过，可发布运输订单。
      <router-link to="/shipper/certification" class="link">查看认证信息</router-link>
    </NoticeBar>
    <NoticeBar v-else tone="warning">
      当前认证状态：<StatusPill :text="auth.user?.auth_status ?? '未提交'" />。认证未达审核通过，发布运输订单将被阻断。
      <router-link to="/shipper/certification" class="link">前往认证</router-link>
    </NoticeBar>

    <div class="panel-gap" />

    <section class="panel">
      <div class="panel-head">
        <span class="panel-title">最近运输订单</span>
        <span class="panel-hint"><router-link to="/shipper/orders" class="link">查看全部</router-link></span>
      </div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!recentOrders.length" text="暂无运输订单" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">编号</th><th>货物</th><th>发货地 → 收货地</th><th>订单状态</th><th>发布时间</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="order in recentOrders" :key="order.id">
                <td class="num">{{ order.order_no }}</td>
                <td>{{ shortCargo(order) }}</td>
                <td>{{ shortPlace(order.shipping_snapshot) }} → {{ shortPlace(order.receiving_snapshot) }}</td>
                <td><StatusPill :text="order.status" /></td>
                <td class="num">{{ time(order.created_at) }}</td>
                <td class="ops">
                  <el-button type="primary" link @click="router.push(`/shipper/orders/${order.id}/progress`)">查看进度</el-button>
                  <el-button type="primary" link @click="router.push('/shipper/orders')">查看详情</el-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">系统通知</span></div>
      <div class="panel-body">
        <EmptyState v-if="!notices.length" text="暂无系统通知" />
        <ul v-else class="list-simple">
          <li v-for="notice in notices" :key="notice.id">
            <span>{{ notice.title }}<span class="notice-body"> · {{ notice.body }}</span></span>
            <span class="meta">{{ time(notice.created_at) }}</span>
          </li>
        </ul>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">快捷入口</span></div>
      <div class="panel-body quick-links">
        <el-button @click="router.push('/shipper/warehouses')">仓库管理</el-button>
        <el-button @click="router.push('/shipper/orders/new')">发布运输订单</el-button>
        <el-button @click="router.push('/shipper/orders')">我的订单</el-button>
      </div>
    </section>
  </section>
</template>

<style scoped>
.panel-gap { height: var(--space-4); }
.link { color: var(--color-accent); }
.link:hover { color: var(--color-accent-hover); }
.notice-body { color: var(--color-text-3); }
.quick-links { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.quick-links .el-button + .el-button { margin-left: 0; }
</style>
