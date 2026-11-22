<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as orderApi from '@/api/order'
import type { Order, OrderFilter, OrderStatus } from '@/types/order'

const router = useRouter()
const rows = ref<Order[]>([])
const loading = ref(false)
const detail = ref<Order | null>(null)
const filter = reactive<OrderFilter>({})

const statuses: OrderStatus[] = [
  '待承接',
  '已承接',
  '运输中',
  '已完成',
  '取消处理中',
  '已取消',
  '异常处理中',
]

function place(snapshot: { province: string; city: string; district: string; detail_address: string }): string {
  return `${snapshot.province}${snapshot.city}${snapshot.district}${snapshot.detail_address}`
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

async function openDetail(order: Order): Promise<void> {
  try {
    detail.value = await orderApi.fetchOrder(order.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取订单详情失败')
  }
}

onMounted(load)
</script>

<template>
  <section class="orders">
    <div class="toolbar">
      <h1 class="page-title">我的订单</h1>
      <el-button type="primary" @click="router.push('/shipper/orders/new')">发布运输订单</el-button>
    </div>

    <div class="toolbar">
      <el-input v-model="filter.order_no" class="field" placeholder="订单号" clearable />
      <el-select v-model="filter.status" class="field" placeholder="全部状态" clearable>
        <el-option v-for="status in statuses" :key="status" :label="status" :value="status" />
      </el-select>
      <el-input v-model="filter.cargo_name" class="field" placeholder="货物名称" clearable />
      <el-input v-model="filter.shipping_place" class="field" placeholder="发货地" clearable />
      <el-input v-model="filter.receiving_place" class="field" placeholder="收货地" clearable />
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="order_no" label="订单号" width="170" />
      <el-table-column prop="cargo_name" label="货物名称" />
      <el-table-column label="发货地">
        <template #default="{ row }">{{ place(row.shipping_snapshot) }}</template>
      </el-table-column>
      <el-table-column label="收货地">
        <template #default="{ row }">{{ place(row.receiving_snapshot) }}</template>
      </el-table-column>
      <el-table-column label="运费报价">
        <template #default="{ row }">
          {{ row.quote_method === '固定' ? `${row.quote_amount_yuan} 元` : row.quote_method }}
        </template>
      </el-table-column>
      <el-table-column label="状态">
        <template #default="{ row }">
          <el-tag :type="row.status === '待承接' ? 'warning' : 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="发布时间" width="180" />
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button type="primary" link @click="openDetail(row)">详情</el-button>
          <el-button link @click="router.push(`/shipper/orders/${row.id}/progress`)">进度</el-button>
          <el-button
            v-if="row.status === '待承接' || row.status === '已承接'"
            link
            type="danger"
            @click="router.push(`/shipper/orders/${row.id}/cancel`)"
          >
            取消
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <span>暂无运输订单，点击「发布运输订单」发布第一条货源。</span>
      </template>
    </el-table>

    <el-dialog v-model="detail" title="运输订单详情" width="760px">
      <template v-if="detail">
        <h3 class="detail-title">货物与要求</h3>
        <p class="detail-row">货物：{{ detail.cargo_name }} · {{ detail.cargo_type }} · {{ detail.quantity }} · {{ detail.weight }} · {{ detail.volume }}</p>
        <p class="detail-row">包装：{{ detail.packaging }}；备注：{{ detail.cargo_remarks || '无' }}</p>
        <p class="detail-row">运输要求：{{ detail.vehicle_type }} / {{ detail.vehicle_length }} / {{ detail.load_requirement }}</p>
        <p class="detail-row">
          特殊要求：{{ detail.cold_chain ? '冷链 ' : '' }}{{ detail.rain_protection ? '防雨 ' : '' }}{{ detail.enclosed_body ? '厢式 ' : '' }}{{ detail.special_loading ? '特殊装载' : '' }}
        </p>
        <h3 class="detail-title">发货快照</h3>
        <p class="detail-row">
          {{ detail.shipping_snapshot.name }} · {{ detail.shipping_snapshot.contact }} ·
          {{ detail.shipping_snapshot.phone }} · {{ place(detail.shipping_snapshot) }}
        </p>
        <h3 class="detail-title">收货快照</h3>
        <p class="detail-row">
          {{ detail.receiving_snapshot.name }} · {{ detail.receiving_snapshot.contact }} ·
          {{ detail.receiving_snapshot.phone }} · {{ place(detail.receiving_snapshot) }}
        </p>
        <h3 class="detail-title">运费报价（仅货主与物流公司可见）</h3>
        <p class="detail-row">
          {{ detail.quote_method }} · {{ detail.quote_amount_yuan }} 元 ·
          接受议价：{{ detail.accept_bargain ? '是' : '否' }}
        </p>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.orders {
  padding: var(--space-2) 0;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.page-title {
  margin: 0 var(--space-4) 0 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.field {
  width: 160px;
}

.detail-title {
  margin: var(--space-4) 0 var(--space-2);
  font-size: var(--font-size-md);
}

.detail-row {
  margin: 0 0 var(--space-1);
  color: var(--color-text-muted);
}
</style>
