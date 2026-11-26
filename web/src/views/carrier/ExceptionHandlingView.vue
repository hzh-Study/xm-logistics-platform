<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCarrierExceptions, handleException } from '@/api/exception'
import { listDrivers } from '@/api/driver'
import { listVehicles } from '@/api/vehicle'
import PageHeader from '@/components/PageHeader.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import PhotoGrid from '@/components/PhotoGrid.vue'
import type { Driver } from '@/types/driver'
import type { Vehicle } from '@/types/vehicle'
import type { Anomaly, ExceptionView, HandlingPayload, HandlingResult } from '@/types/exception'

const route = useRoute()
const taskId = Number(route.params.taskId)
const view = ref<ExceptionView | null>(null)
const drivers = ref<Driver[]>([])
const vehicles = ref<Vehicle[]>([])
const loading = ref(false)
const busyId = ref<number | null>(null)
const terminateTarget = ref<Anomaly | null>(null)
const terminateOpen = ref(false)

const results: HandlingResult[] = [
  '继续运输', '调整送达时间', '更换车辆', '更换司机', '重新安排运输', '终止运输',
]

interface FormState {
  result: HandlingResult
  detail: string
  new_vehicle_id: number | null
  new_driver_account_id: number | null
  adjusted_deliver_at: string
}
const forms = reactive<Record<number, FormState>>({})

function formFor(id: number): FormState {
  if (!forms[id]) {
    forms[id] = {
      result: '继续运输', detail: '', new_vehicle_id: null,
      new_driver_account_id: null, adjusted_deliver_at: '',
    }
  }
  return forms[id]
}

function handlingFor(anomalyId: number) {
  return view.value?.handling_records.find((record) => record.anomaly_id === anomalyId) ?? null
}

function displayKind(kind: string): string {
  const map: Record<string, string> = { 故障: '车辆故障', 货物异常: '货物问题', 其他: '其它' }
  return map[kind] ?? kind
}

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function toIso(value: string): string {
  if (value.length === 16) return `${value}:00+00:00`
  if (value.length === 19) return `${value}+00:00`
  return value
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [exceptionView, driverRows, vehicleRows] = await Promise.all([
      getCarrierExceptions(taskId), listDrivers(), listVehicles(),
    ])
    view.value = exceptionView
    drivers.value = driverRows
    vehicles.value = vehicleRows
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取异常记录失败')
  } finally {
    loading.value = false
  }
}

function askSubmit(anomaly: Anomaly): void {
  const form = formFor(anomaly.id)
  if (form.result === '终止运输') {
    if (!form.detail.trim()) {
      ElMessage.warning('终止运输必须填写处理说明与原因')
      return
    }
    terminateTarget.value = anomaly
    terminateOpen.value = true
    return
  }
  void submit(anomaly)
}

async function submit(anomaly: Anomaly): Promise<void> {
  const form = formFor(anomaly.id)
  const payload: HandlingPayload = { result: form.result, detail: form.detail.trim() }
  if (form.result === '更换车辆' && form.new_vehicle_id) payload.new_vehicle_id = form.new_vehicle_id
  if (form.result === '更换司机' && form.new_driver_account_id) payload.new_driver_account_id = form.new_driver_account_id
  if (form.result === '调整送达时间' && form.adjusted_deliver_at) payload.adjusted_deliver_at = toIso(form.adjusted_deliver_at)
  busyId.value = anomaly.id
  try {
    await handleException(taskId, anomaly.id, payload)
    ElMessage.success('异常处理记录已追加')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '处理失败')
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="异常处理" :subtitle="`${view?.task_no ?? '—'} · 结果追加为异常处理记录，不覆盖原文`" />

    <EmptyState v-if="!view?.anomalies.length" text="该任务暂无异常记录" />

    <section v-for="anomaly in view?.anomalies ?? []" :key="anomaly.id" class="panel">
      <div class="panel-head">
        <span class="panel-title">{{ anomaly.anomaly_no }} · {{ displayKind(anomaly.kind) }}</span>
        <span class="panel-hint">{{ anomaly.actor }} · {{ stamp(anomaly.occurred_at) }}</span>
      </div>
      <div class="panel-body">
        <dl class="kv">
          <dt>异常任务</dt><dd class="num">{{ anomaly.task_no }}</dd>
          <dt>异常说明</dt><dd>{{ anomaly.detail }}</dd>
        </dl>
        <PhotoGrid v-if="anomaly.photos.length" :photos="anomaly.photos" />

        <div class="panel-gap" />
        <NoticeBar v-if="handlingFor(anomaly.id)" tone="info">
          处理结果：<StatusPill :text="String(handlingFor(anomaly.id)?.result ?? '')" /> · {{ handlingFor(anomaly.id)?.detail }}（{{ stamp(handlingFor(anomaly.id)?.created_at ?? '') }}）
        </NoticeBar>

        <template v-if="!handlingFor(anomaly.id)">
          <div class="form-grid section-gap">
            <div class="field">
              <label class="field__label"><span class="field__req">*</span>处理结果</label>
              <el-select v-model="formFor(anomaly.id).result">
                <el-option v-for="item in results" :key="item" :label="item" :value="item" />
              </el-select>
            </div>
            <div v-if="formFor(anomaly.id).result === '调整送达时间'" class="field">
              <label class="field__label">调整后的送达时间</label>
              <el-date-picker v-model="formFor(anomaly.id).adjusted_deliver_at" type="datetime" value-format="YYYY-MM-DDTHH:mm" class="date-input" />
            </div>
            <div v-if="formFor(anomaly.id).result === '更换车辆'" class="field">
              <label class="field__label">新车辆</label>
              <el-select v-model="formFor(anomaly.id).new_vehicle_id" placeholder="全部" style="width: 100%">
                <el-option v-for="vehicle in vehicles" :key="vehicle.id" :label="`${vehicle.plate_no} · ${vehicle.availability}`" :value="vehicle.id" />
              </el-select>
            </div>
            <div v-if="formFor(anomaly.id).result === '更换司机'" class="field">
              <label class="field__label">新司机</label>
              <el-select v-model="formFor(anomaly.id).new_driver_account_id" placeholder="全部" style="width: 100%">
                <el-option v-for="driver in drivers" :key="driver.account_id" :label="`${driver.name} · ${driver.availability}`" :value="driver.account_id" />
              </el-select>
            </div>
            <div class="field field--wide">
              <label class="field__label">处理说明（终止运输时必填）</label>
              <el-input v-model="formFor(anomaly.id).detail" type="textarea" :rows="3" placeholder="可补充说明或原因" />
            </div>
          </div>
          <div class="form-actions">
            <el-button type="primary" :loading="busyId === anomaly.id" @click="askSubmit(anomaly)">提交处置</el-button>
          </div>
        </template>

        <div v-if="view?.handling_records.some((r) => r.anomaly_id === anomaly.id)" class="records">
          <h3 class="records-title">追加处理记录</h3>
          <ul class="record-list">
            <li v-for="record in view.handling_records.filter((r) => r.anomaly_id === anomaly.id)" :key="record.id">
              <StatusPill :text="String(record.result)" />
              <span>{{ record.detail }}</span>
              <span class="record-meta">{{ record.actor }} · {{ stamp(record.created_at) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <ConfirmDialog v-model="terminateOpen" title="确认终止运输" confirm-text="确认终止" danger @confirm="terminateTarget && submit(terminateTarget)">
      终止运输会将订单置为「已取消」并写明原因，确认继续？
    </ConfirmDialog>
  </section>
</template>

<style scoped>
.panel-gap { height: var(--space-4); }
.section-gap { margin-top: var(--space-4); }
.field--wide { grid-column: 1 / -1; }
.date-input { width: 100%; }
.records { margin-top: var(--space-5); }
.records-title { margin: 0 0 var(--space-2); font-size: var(--font-size-sm); font-weight: 600; }
.record-list { margin: 0; padding: 0; list-style: none; }
.record-list li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3); padding: var(--space-2) 0; border-bottom: 1px solid var(--color-border); font-size: var(--font-size-sm); }
.record-list li:last-child { border-bottom: 0; }
.record-meta { color: var(--color-text-3); font-size: var(--font-size-xs); }
</style>
