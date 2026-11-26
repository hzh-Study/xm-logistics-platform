<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { CarrierSummary } from '@/types/carrier'
import type { VehicleTransfer } from '@/types/admin'

const rows = ref<VehicleTransfer[]>([])
const carriers = ref<CarrierSummary[]>([])
const loading = ref(false)
const saving = ref(false)
const createOpen = ref(false)
const form = reactive({ vehicle_id: undefined as number | undefined, to_carrier_id: undefined as number | undefined, reason: '' })
const filter = reactive({ vehicle_id: undefined as number | undefined })

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [transferRows, carrierRows] = await Promise.all([
      adminApi.fetchVehicleTransfers(filter.vehicle_id),
      adminApi.listCarriers(),
    ])
    rows.value = transferRows
    carriers.value = carrierRows
  } catch (error) {
    ElMessage.error(errorText(error, '加载转籍历史失败'))
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  form.vehicle_id = undefined
  form.to_carrier_id = undefined
  form.reason = ''
  createOpen.value = true
}

async function submit(): Promise<void> {
  const vehicleId = form.vehicle_id
  const carrierId = form.to_carrier_id
  if (!vehicleId || !carrierId || !form.reason.trim()) {
    ElMessage.warning('车辆、转入物流公司与转籍原因必填')
    return
  }
  saving.value = true
  try {
    const result = await adminApi.transferVehicle({ vehicle_id: vehicleId, to_carrier_id: carrierId, reason: form.reason })
    ElMessage.success(`车辆 ${result.plate_no} 已完成转籍`)
    createOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(errorText(error, '车辆转籍失败，若车辆存在进行中任务将被驳回'))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="车辆转籍" subtitle="仅当车辆无进行中任务时可转籍 · 审批后历史任务车辆数据保持有效">
      <template #actions><el-button type="primary" @click="openCreate">执行转籍</el-button></template>
    </PageHeader>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="tr-vehicle">车辆 ID</label><el-input id="tr-vehicle" v-model="filter.vehicle_id" placeholder="请输入车辆 ID" clearable /></div>
      </div>
      <div class="filter-actions"><el-button type="primary" @click="load">查询</el-button></div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">转籍历史</span><span class="panel-hint">历史记录只读追加，原任务车辆信息不改写</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!rows.length" text="暂无车辆转籍记录" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th class="num">转籍编号</th><th class="num">车牌号</th><th>原公司 → 目标公司</th><th>操作人</th><th class="num">时间</th><th>转籍原因</th></tr></thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id">
                <td class="num">{{ row.transfer_no }}</td>
                <td class="num">{{ row.plate_no }}</td>
                <td>公司 #{{ row.before_carrier_id }} → 公司 #{{ row.after_carrier_id }}</td>
                <td>{{ row.actor }}</td>
                <td class="num">{{ stamp(row.created_at) }}</td>
                <td>{{ row.reason }}</td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ rows.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="createOpen" title="执行车辆转籍">
      <template #body>
        <NoticeBar tone="warning">系统校验：仅当车辆当前无进行中运输任务时放行；转籍后原任务记录的车辆信息不改写。</NoticeBar>
        <form class="drawer-form">
          <div class="field"><label class="field__label"><span class="field__req">*</span>车辆 ID</label><el-input v-model="form.vehicle_id" placeholder="请输入车辆 ID" /></div>
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>目标物流公司</label>
            <el-select v-model="form.to_carrier_id" placeholder="全部" style="width: 100%">
              <el-option v-for="carrier in carriers" :key="carrier.account_id" :label="carrier.company_name" :value="carrier.account_id" />
            </el-select>
          </div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>转籍原因</label><el-input v-model="form.reason" type="textarea" :rows="3" /></div>
        </form>
      </template>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">确认转籍</el-button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.drawer-form { padding-top: var(--space-4); }
</style>
