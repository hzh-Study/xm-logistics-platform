<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import PhotoGrid from '@/components/PhotoGrid.vue'
import type { Order, OrderStatus } from '@/types/order'

const rows = ref<Order[]>([])
const loading = ref(false)
const detail = ref<Order | null>(null)
const detailOpen = ref(false)
const filter = reactive({ order_no: '', shipper: '', company: '', status: '' as OrderStatus | '', published_from: '', published_to: '' })
const statuses: OrderStatus[] = ['待承接', '已承接', '运输中', '已完成', '取消处理中', '已取消', '异常处理中']

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function place(snapshot: { province: string; city: string }): string {
  return `${snapshot.province}${snapshot.city}`
}

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

function reset(): void {
  filter.order_no = ''
  filter.shipper = ''
  filter.company = ''
  filter.status = ''
  filter.published_from = ''
  filter.published_to = ''
  void load()
}

async function openDetail(order: Order): Promise<void> {
  try {
    detail.value = await adminApi.fetchPlatformOrder(order.id)
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取订单详情失败')
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="运输订单查询" subtitle="平台级只读查询 · 按编号、货主、物流公司、状态、发布时间" />

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="ao-no">订单编号</label><el-input id="ao-no" v-model="filter.order_no" placeholder="请输入订单编号" clearable /></div>
        <div class="field"><label class="field__label" for="ao-shipper">货主</label><el-input id="ao-shipper" v-model="filter.shipper" placeholder="请输入货主" clearable /></div>
        <div class="field"><label class="field__label" for="ao-company">物流公司</label><el-input id="ao-company" v-model="filter.company" placeholder="请输入物流公司" clearable /></div>
        <div class="field">
          <label class="field__label" for="ao-status">订单状态</label>
          <el-select id="ao-status" v-model="filter.status" placeholder="全部" clearable>
            <el-option v-for="item in statuses" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field"><label class="field__label">发布时间</label><el-date-picker v-model="filter.published_from" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" class="date-input" /></div>
        <div class="field"><label class="field__label">发布时间（止）</label><el-date-picker v-model="filter.published_to" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" class="date-input" /></div>
      </div>
      <div class="filter-actions">
        <el-button @click="reset">重置</el-button>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">订单列表</span><span class="panel-hint">只读，不提供改写业务记录的操作</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!rows.length" text="暂无运输订单" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">订单编号</th><th>货主</th><th>物流公司</th><th>货物</th><th>订单状态</th><th class="num">发布时间</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id">
                <td class="num">{{ row.order_no }}</td>
                <td>货主 #{{ row.shipper_id }}</td>
                <td>{{ row.carrier_id ? `公司 #${row.carrier_id}` : '—' }}</td>
                <td>{{ [row.cargo_name, row.quantity].filter(Boolean).join(' · ') }}</td>
                <td><StatusPill :text="row.status" /></td>
                <td class="num">{{ stamp(row.created_at) }}</td>
                <td class="ops"><el-button type="primary" link @click="openDetail(row)">查看</el-button></td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ rows.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="detailOpen" title="运输订单详情">
      <template #body>
        <NoticeBar v-if="detail" tone="info">管理员只读查看，不提供改写订单、任务、打卡或费用记录的操作。</NoticeBar>
        <dl v-if="detail" class="kv section-gap">
          <dt>订单编号</dt><dd class="num">{{ detail.order_no }}</dd>
          <dt>订单状态</dt><dd><StatusPill :text="detail.status" /></dd>
          <dt>货主</dt><dd>货主 #{{ detail.shipper_id }}</dd>
          <dt>物流公司</dt><dd>{{ detail.carrier_id ? `公司 #${detail.carrier_id}` : '—' }}</dd>
          <dt>货物</dt><dd>{{ [detail.cargo_name, detail.cargo_type, detail.quantity, detail.weight].filter(Boolean).join(' · ') }}</dd>
          <dt>发货快照</dt><dd>{{ place(detail.shipping_snapshot) }}{{ detail.shipping_snapshot.detail_address }}</dd>
          <dt>收货快照</dt><dd>{{ place(detail.receiving_snapshot) }}{{ detail.receiving_snapshot.detail_address }}</dd>
          <dt>发布时间</dt><dd class="num">{{ stamp(detail.created_at) }}</dd>
        </dl>
        <PhotoGrid v-if="detail?.cargo_photos.length" :photos="detail.cargo_photos" />
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.date-input { width: 100%; }
.section-gap { margin-top: var(--space-4); }
</style>
