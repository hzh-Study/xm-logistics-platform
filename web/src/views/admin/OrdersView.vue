<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import type { Order, OrderStatus } from '@/types/order'

const rows = ref<Order[]>([])
const loading = ref(false)
const detail = ref<Order | null>(null)
const filter = reactive({
  order_no: '',
  shipper: '',
  company: '',
  status: '' as OrderStatus | '',
  published_from: '',
  published_to: '',
})

const statuses: OrderStatus[] = [
  '待承接',
  '已承接',
  '运输中',
  '已完成',
  '取消处理中',
  '已取消',
  '异常处理中',
]

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await adminApi.fetchPlatformOrders({ ...filter })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载订单失败')
  } finally {
    loading.value = false
  }
}

async function openDetail(order: Order): Promise<void> {
  try {
    detail.value = await adminApi.fetchPlatformOrder(order.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取订单详情失败')
  }
}

onMounted(load)
</script>

<template>
  <section class="orders">
    <h1 class="page-title">全平台运输订单</h1>

    <div class="toolbar">
      <el-input v-model="filter.order_no" class="field" placeholder="订单编号" clearable />
      <el-input v-model="filter.shipper" class="field" placeholder="货主名称/手机号" clearable />
      <el-input v-model="filter.company" class="field" placeholder="承运公司" clearable />
      <el-select v-model="filter.status" class="field" placeholder="全部状态" clearable>
        <el-option v-for="status in statuses" :key="status" :label="status" :value="status" />
      </el-select>
      <el-input v-model="filter.published_from" class="field-wide" placeholder="发布起始 ISO 8601" clearable />
      <el-input v-model="filter.published_to" class="field-wide" placeholder="发布截止 ISO 8601" clearable />
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="order_no" label="订单编号" width="170" />
      <el-table-column prop="cargo_name" label="货物名称" />
      <el-table-column label="货主账号" prop="shipper_id" width="110" />
      <el-table-column label="承运公司账号" prop="carrier_id" width="130">
        <template #default="{ row }">{{ row.carrier_id ?? '待承接' }}</template>
      </el-table-column>
      <el-table-column label="状态">
        <template #default="{ row }">
          <el-tag :type="row.status === '已完成' ? 'success' : 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="发布时间" width="200" />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button type="primary" link @click="openDetail(row)">详情</el-button>
        </template>
      </el-table-column>
      <template #empty><span>暂无符合条件的运输订单。</span></template>
    </el-table>

    <el-dialog v-model="detail" title="运输订单详情" width="720px">
      <template v-if="detail">
        <p class="detail-row">编号：{{ detail.order_no }} · 状态：{{ detail.status }}</p>
        <p class="detail-row">货物：{{ detail.cargo_name }} · {{ detail.quantity }} · {{ detail.weight }}</p>
        <p class="detail-row">发货：{{ detail.shipping_snapshot.name }} · {{ detail.shipping_snapshot.phone }}</p>
        <p class="detail-row">收货：{{ detail.receiving_snapshot.name }} · {{ detail.receiving_snapshot.phone }}</p>
        <p class="detail-row">运费报价：{{ detail.quote_method }} · {{ detail.quote_amount_yuan }} 元</p>
        <p class="detail-row">发布时间：{{ detail.created_at }}</p>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.orders {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0 0 var(--space-6);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.field {
  width: 150px;
}

.field-wide {
  width: 210px;
}

.detail-row {
  margin: 0 0 var(--space-2);
  color: var(--color-text-muted);
}
</style>
