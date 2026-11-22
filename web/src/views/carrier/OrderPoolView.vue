<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as orderApi from '@/api/order'
import type { Order, PoolFilter } from '@/types/order'

const rows = ref<Order[]>([])
const loading = ref(false)
const detail = ref<Order | null>(null)
const filter = reactive<PoolFilter>({})

function place(snapshot: {
  province: string
  city: string
  district: string
  detail_address: string
}): string {
  return `${snapshot.province}${snapshot.city}${snapshot.district}${snapshot.detail_address}`
}

function quote(row: Order): string {
  return row.quote_method === '固定' ? `${row.quote_amount_yuan} 元` : row.quote_method
}

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await orderApi.fetchPool({ ...filter })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载订单池失败')
  } finally {
    loading.value = false
  }
}

function reset(): void {
  for (const key of Object.keys(filter) as (keyof PoolFilter)[]) {
    delete filter[key]
  }
  void load()
}

async function openDetail(order: Order): Promise<void> {
  try {
    detail.value = await orderApi.fetchPoolOrder(order.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取货源详情失败')
  }
}

async function accept(order: Order): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认承接货源 ${order.order_no}？承接成功后将唯一归属本公司，其他物流公司无法再次承接。`,
      '承接确认',
      { type: 'warning', confirmButtonText: '确认承接', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const result = await orderApi.acceptOrder(order.id)
    ElMessage.success(`承接成功，订单 ${result.order_no} 已归属本公司`)
    detail.value = null
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '承接失败')
  }
}

onMounted(load)
</script>

<template>
  <section class="pool">
    <div class="toolbar">
      <h1 class="page-title">订单池</h1>
      <span class="hint">仅展示待承接货源，先到先得</span>
    </div>

    <div class="toolbar">
      <el-input v-model="filter.shipping_place" class="field" placeholder="发货地" clearable />
      <el-input v-model="filter.receiving_place" class="field" placeholder="收货地" clearable />
      <el-input v-model="filter.cargo_type" class="field" placeholder="货物类型" clearable />
      <el-input v-model="filter.vehicle_type" class="field" placeholder="车辆类型" clearable />
      <el-input v-model="filter.weight" class="field" placeholder="重量" clearable />
      <el-input v-model="filter.quote_min_yuan" class="field" placeholder="最低运费(元)" clearable />
      <el-input v-model="filter.quote_max_yuan" class="field" placeholder="最高运费(元)" clearable />
      <el-input v-model="filter.published_from" class="field" placeholder="发布起(ISO 时间)" clearable />
      <el-input v-model="filter.published_to" class="field" placeholder="发布止(ISO 时间)" clearable />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="reset">重置</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="order_no" label="订单号" width="170" />
      <el-table-column prop="cargo_name" label="货物名称" />
      <el-table-column prop="cargo_type" label="货物类型" />
      <el-table-column prop="weight" label="重量" />
      <el-table-column label="发货地">
        <template #default="{ row }">{{ place(row.shipping_snapshot) }}</template>
      </el-table-column>
      <el-table-column label="收货地">
        <template #default="{ row }">{{ place(row.receiving_snapshot) }}</template>
      </el-table-column>
      <el-table-column prop="vehicle_type" label="车型要求" />
      <el-table-column label="运费报价">
        <template #default="{ row }">{{ quote(row) }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="发布时间" width="180" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button type="primary" link @click="openDetail(row)">详情</el-button>
          <el-button type="primary" link @click="accept(row)">承接</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <span>暂无待承接货源，请调整筛选条件后再试。</span>
      </template>
    </el-table>

    <el-dialog v-model="detail" title="货源详情" width="760px">
      <template v-if="detail">
        <h3 class="detail-title">货物与要求</h3>
        <p class="detail-row">
          货物：{{ detail.cargo_name }} · {{ detail.cargo_type }} · {{ detail.quantity }} ·
          {{ detail.weight }} · {{ detail.volume }}
        </p>
        <p class="detail-row">包装：{{ detail.packaging }}；备注：{{ detail.cargo_remarks || '无' }}</p>
        <p class="detail-row">
          运输要求：{{ detail.vehicle_type }} / {{ detail.vehicle_length }} /
          {{ detail.load_requirement }}
        </p>
        <p class="detail-row">
          特殊要求：{{ detail.cold_chain ? '冷链 ' : '' }}{{ detail.rain_protection ? '防雨 ' : ''
          }}{{ detail.enclosed_body ? '厢式 ' : '' }}{{ detail.special_loading ? '特殊装载' : '' }}
        </p>
        <p class="detail-row">其他服务：{{ detail.other_services || '无' }}；要求备注：{{ detail.transport_remarks || '无' }}</p>
        <p class="detail-row">货物照片：{{ detail.cargo_photos.join('、') || '无' }}</p>
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
        <h3 class="detail-title">运费报价（仅货主与物流公司可见，不构成结算）</h3>
        <p class="detail-row">
          {{ detail.quote_method }} · {{ detail.quote_amount_yuan }} 元 ·
          接受议价：{{ detail.accept_bargain ? '是' : '否' }} · {{ detail.quote_remarks || '无备注' }}
        </p>
      </template>
      <template #footer>
        <el-button @click="detail = null">关闭</el-button>
        <el-button v-if="detail" type="primary" @click="accept(detail)">承接该订单</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.pool {
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

.hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
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
