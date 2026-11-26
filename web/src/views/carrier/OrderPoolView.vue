<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as orderApi from '@/api/order'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import StatusPill from '@/components/StatusPill.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import PhotoGrid from '@/components/PhotoGrid.vue'
import type { Order, PoolFilter } from '@/types/order'

const rows = ref<Order[]>([])
const loading = ref(false)
const detail = ref<Order | null>(null)
const detailOpen = ref(false)
const acceptTarget = ref<Order | null>(null)
const acceptOpen = ref(false)
const accepting = ref(false)
const filter = reactive<PoolFilter>({})

const CARGO_TYPES = ['钢材', '建材', '机电设备', '化工品', '冷链食品']
const VEHICLE_TYPES = ['平板车', '厢式货车', '高栏车']

function place(snapshot: { province: string; city: string; district: string; detail_address: string }): string {
  return `${snapshot.province}${snapshot.city}${snapshot.district}${snapshot.detail_address}`
}

function shortPlace(snapshot: { province: string; city: string }): string {
  return `${snapshot.province}${snapshot.city}`
}

function quote(row: Order): string {
  return `¥ ${row.quote_amount_yuan || '0.00'}${row.quote_method === '固定' ? '（固定价）' : ''}`
}

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
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
  for (const key of Object.keys(filter) as (keyof PoolFilter)[]) delete filter[key]
  void load()
}

async function openDetail(order: Order): Promise<void> {
  try {
    detail.value = await orderApi.fetchPoolOrder(order.id)
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取货源详情失败')
  }
}

function askAccept(order: Order): void {
  acceptTarget.value = order
  acceptOpen.value = true
}

async function accept(): Promise<void> {
  const target = acceptTarget.value
  if (!target) return
  accepting.value = true
  try {
    const result = await orderApi.acceptOrder(target.id)
    ElMessage.success(`承接成功，订单 ${result.order_no} 已归属本公司`)
    detailOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '承接失败')
  } finally {
    accepting.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="订单池" :subtitle="`当前可承接货源 ${rows.length} 条 · 先到先得`">
      <template #actions><el-button @click="load">刷新</el-button></template>
    </PageHeader>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="pool-ship">发货地</label><el-input id="pool-ship" v-model="filter.shipping_place" placeholder="请输入发货地" clearable /></div>
        <div class="field"><label class="field__label" for="pool-recv">收货地</label><el-input id="pool-recv" v-model="filter.receiving_place" placeholder="请输入收货地" clearable /></div>
        <div class="field">
          <label class="field__label" for="pool-type">货物类型</label>
          <el-select id="pool-type" v-model="filter.cargo_type" placeholder="全部" clearable>
            <el-option v-for="item in CARGO_TYPES" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="pool-vehicle">车型</label>
          <el-select id="pool-vehicle" v-model="filter.vehicle_type" placeholder="全部" clearable>
            <el-option v-for="item in VEHICLE_TYPES" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field"><label class="field__label" for="pool-weight">重量（吨）</label><el-input id="pool-weight" v-model="filter.weight" placeholder="如：20" clearable /></div>
        <div class="field"><label class="field__label">发布时间</label><el-date-picker v-model="filter.published_from" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" class="date-input" /></div>
        <div class="field"><label class="field__label">发布时间（止）</label><el-date-picker v-model="filter.published_to" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" class="date-input" /></div>
        <div class="field"><label class="field__label" for="pool-qmin">运费下限</label><el-input id="pool-qmin" v-model="filter.quote_min_yuan" placeholder="元" clearable /></div>
        <div class="field"><label class="field__label" for="pool-qmax">运费上限</label><el-input id="pool-qmax" v-model="filter.quote_max_yuan" placeholder="元" clearable /></div>
      </div>
      <div class="filter-actions">
        <el-button @click="reset">重置</el-button>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">可承接货源</span><span class="panel-hint">货源为待承接运输订单的视图 · V1 先到先得，无竞价</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!rows.length" text="暂无待承接的运输订单" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">订单编号</th><th>货物</th><th>发货地</th><th>收货地</th><th>车辆要求</th><th class="num">运费报价</th><th class="num">发布时间</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id">
                <td class="num">{{ row.order_no }}</td>
                <td>{{ [row.cargo_name, row.quantity, row.volume].filter(Boolean).join(' · ') }}</td>
                <td>{{ shortPlace(row.shipping_snapshot) }}</td>
                <td>{{ shortPlace(row.receiving_snapshot) }}</td>
                <td>{{ [row.vehicle_type, row.vehicle_length].filter(Boolean).join(' / ') }}</td>
                <td class="num">{{ quote(row) }}</td>
                <td class="num">{{ stamp(row.created_at) }}</td>
                <td class="ops">
                  <el-button type="primary" link @click="openDetail(row)">查看货源</el-button>
                  <el-button type="primary" link @click="askAccept(row)">承接</el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ rows.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="detailOpen" :title="`货源详情 · ${detail?.order_no ?? ''}`">
      <template #body>
        <template v-if="detail">
          <dl class="kv">
            <dt>订单状态</dt><dd><StatusPill :text="detail.status" /></dd>
            <dt>货物</dt><dd>{{ [detail.cargo_name, detail.quantity, detail.volume].filter(Boolean).join(' · ') }}</dd>
            <dt>发货快照</dt><dd>{{ place(detail.shipping_snapshot) }} · {{ detail.shipping_snapshot.contact }} {{ detail.shipping_snapshot.phone }}</dd>
            <dt>收货快照</dt><dd>{{ place(detail.receiving_snapshot) }} · {{ detail.receiving_snapshot.contact }} {{ detail.receiving_snapshot.phone }}</dd>
            <dt>运输要求</dt><dd>{{ [detail.vehicle_type, detail.vehicle_length, detail.load_requirement && `载重 ${detail.load_requirement} 吨`, detail.rain_protection && '防雨', detail.special_loading && '特殊装卸'].filter(Boolean).join(' / ') }}</dd>
            <dt>运费报价</dt><dd class="num">{{ quote(detail) }}（接受议价标记：{{ detail.accept_bargain ? '是' : '否' }}）</dd>
            <dt>发布时间</dt><dd class="num">{{ stamp(detail.created_at) }}</dd>
            <dt>备注</dt><dd>{{ detail.cargo_remarks || '—' }}</dd>
          </dl>
          <PhotoGrid v-if="detail.cargo_photos.length" :photos="detail.cargo_photos" />
          <p class="accept-hint">承接前请确认：具备对应运力、有可用司机与车辆、时间可满足要求，并接受当前运费报价。</p>
        </template>
      </template>
      <template #footer>
        <el-button @click="detailOpen = false">关闭</el-button>
        <el-button v-if="detail" type="primary" :loading="accepting" @click="askAccept(detail)">确认承接</el-button>
      </template>
    </DetailDrawer>

    <ConfirmDialog
      v-model="acceptOpen"
      title="承接确认"
      confirm-text="确认承接"
      @confirm="accept"
    >
      确认承接货源 {{ acceptTarget?.order_no }}？承接成功后将唯一归属本公司，其他物流公司无法再次承接。
    </ConfirmDialog>
  </section>
</template>

<style scoped>
.date-input { width: 100%; }
.accept-hint { margin: var(--space-4) 0 0; font-size: var(--font-size-sm); color: var(--color-text-2); }
</style>
