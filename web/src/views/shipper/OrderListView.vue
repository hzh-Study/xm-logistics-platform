<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as orderApi from '@/api/order'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import PhotoGrid from '@/components/PhotoGrid.vue'
import type { Order, OrderFilter, OrderStatus } from '@/types/order'

const router = useRouter()
const rows = ref<Order[]>([])
const loading = ref(false)
const detail = ref<Order | null>(null)
const detailOpen = ref(false)
const filter = reactive<OrderFilter>({})

const statuses: OrderStatus[] = [
  '待承接', '已承接', '运输中', '已完成', '取消处理中', '已取消', '异常处理中',
]

function shortPlace(snapshot: { province: string; city: string; district: string }): string {
  return `${snapshot.province}${snapshot.city}${snapshot.district}`
}

function cargo(order: Order): string {
  return [order.cargo_name, order.quantity || order.weight].filter(Boolean).join(' · ')
}

function time(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await orderApi.fetchOrders({ ...filter })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载订单失败')
  } finally {
    loading.value = false
  }
}

function reset(): void {
  Object.keys(filter).forEach((key) => delete (filter as Record<string, unknown>)[key])
  void load()
}

async function openDetail(order: Order): Promise<void> {
  try {
    detail.value = await orderApi.fetchOrder(order.id)
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取订单详情失败')
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="我的订单" subtitle="发布与取消入口 · 全流程状态可追踪">
      <template #actions><el-button type="primary" @click="router.push('/shipper/orders/new')">发布运输订单</el-button></template>
    </PageHeader>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="fl-no">订单编号</label><el-input id="fl-no" v-model="filter.order_no" placeholder="请输入订单编号" clearable /></div>
        <div class="field">
          <label class="field__label" for="fl-status">订单状态</label>
          <el-select id="fl-status" v-model="filter.status" placeholder="全部" clearable>
            <el-option v-for="status in statuses" :key="status" :label="status" :value="status" />
          </el-select>
        </div>
        <div class="field"><label class="field__label" for="fl-cargo">货物名称</label><el-input id="fl-cargo" v-model="filter.cargo_name" placeholder="请输入货物名称" clearable /></div>
        <div class="field"><label class="field__label" for="fl-ship">发货地</label><el-input id="fl-ship" v-model="filter.shipping_place" placeholder="请输入发货地" clearable /></div>
        <div class="field"><label class="field__label" for="fl-recv">收货地</label><el-input id="fl-recv" v-model="filter.receiving_place" placeholder="请输入收货地" clearable /></div>
        <div class="field"><label class="field__label">发布时间</label>
          <el-date-picker v-model="filter.published_from" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" class="date-input" />
        </div>
        <div class="field"><label class="field__label">发布时间（止）</label>
          <el-date-picker v-model="filter.published_to" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" class="date-input" />
        </div>
      </div>
      <div class="filter-actions">
        <el-button @click="reset">重置</el-button>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">订单列表</span><span class="panel-hint">仅展示当前货主发布的运输订单</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!rows.length" text="暂无运输订单，点击「发布运输订单」发布第一条货源。" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">编号</th><th>货物</th><th>发货地 → 收货地</th><th>订单状态</th><th class="num">发布时间</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id">
                <td class="num">{{ row.order_no }}</td>
                <td>{{ cargo(row) }}</td>
                <td>{{ shortPlace(row.shipping_snapshot) }} → {{ shortPlace(row.receiving_snapshot) }}</td>
                <td><StatusPill :text="row.status" /></td>
                <td class="num">{{ time(row.created_at) }}</td>
                <td class="ops">
                  <el-button type="primary" link @click="router.push(`/shipper/orders/${row.id}/progress`)">查看进度</el-button>
                  <el-button type="primary" link @click="openDetail(row)">查看详情</el-button>
                  <el-button v-if="row.status === '待承接' || row.status === '已承接'" type="danger" link @click="router.push(`/shipper/orders/${row.id}/cancel`)">申请取消</el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ rows.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="detailOpen" title="运输订单详情">
      <template #body>
        <template v-if="detail">
          <dl class="kv">
            <dt>订单编号</dt><dd class="num">{{ detail.order_no }}</dd>
            <dt>订单状态</dt><dd><StatusPill :text="detail.status" /></dd>
            <dt>货物</dt><dd>{{ [detail.cargo_name, detail.cargo_type, detail.quantity, detail.weight].filter(Boolean).join(' · ') }}</dd>
            <dt>包装 / 备注</dt><dd>{{ detail.packaging || '—' }} / {{ detail.cargo_remarks || '无' }}</dd>
            <dt>运输要求</dt><dd>{{ [detail.vehicle_type, detail.vehicle_length, detail.load_requirement].filter(Boolean).join(' / ') }}</dd>
            <dt>发货快照</dt><dd>{{ detail.shipping_snapshot.name }} · {{ detail.shipping_snapshot.contact }} · {{ detail.shipping_snapshot.phone }} · {{ shortPlace(detail.shipping_snapshot) }}{{ detail.shipping_snapshot.detail_address }}</dd>
            <dt>收货快照</dt><dd>{{ detail.receiving_snapshot.name }} · {{ detail.receiving_snapshot.contact }} · {{ detail.receiving_snapshot.phone }} · {{ shortPlace(detail.receiving_snapshot) }}{{ detail.receiving_snapshot.detail_address }}</dd>
            <dt>运费报价</dt><dd class="num">{{ detail.quote_method }} · {{ detail.quote_amount_yuan }} 元 · 接受议价：{{ detail.accept_bargain ? '是' : '否' }}</dd>
            <dt>发布时间</dt><dd class="num">{{ time(detail.created_at) }}</dd>
          </dl>
          <PhotoGrid v-if="detail.cargo_photos.length" :photos="detail.cargo_photos" />
        </template>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.date-input { width: 100%; }
</style>
