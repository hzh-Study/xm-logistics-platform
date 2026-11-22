<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCarrierExceptions, handleException } from '@/api/exception'
import type { Anomaly, ExceptionView, HandlingPayload, HandlingResult } from '@/types/exception'

const route = useRoute()
const taskId = Number(route.params.taskId)
const view = ref<ExceptionView | null>(null)
const loading = ref(false)
const busyId = ref<number | null>(null)

const results: HandlingResult[] = [
  '继续运输',
  '调整送达时间',
  '更换车辆',
  '更换司机',
  '重新安排运输',
  '终止运输',
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
      result: '继续运输',
      detail: '',
      new_vehicle_id: null,
      new_driver_account_id: null,
      adjusted_deliver_at: '',
    }
  }
  return forms[id]
}

function handlingFor(anomalyId: number) {
  return view.value?.handling_records.find((record) => record.anomaly_id === anomalyId) ?? null
}

function toIso(value: string): string {
  if (value.length === 16) return `${value}:00+00:00`
  if (value.length === 19) return `${value}+00:00`
  return value
}

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    view.value = await getCarrierExceptions(taskId)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取异常记录失败')
  } finally {
    loading.value = false
  }
}

async function onSubmit(anomaly: Anomaly): Promise<void> {
  const form = formFor(anomaly.id)
  if (!form.detail.trim()) {
    ElMessage.warning('请填写处理说明')
    return
  }
  if (form.result === '终止运输') {
    try {
      await ElMessageBox.confirm('终止运输会将订单置为已取消并写明原因，确认继续？', '确认终止运输', {
        type: 'warning',
      })
    } catch {
      return
    }
  }
  const payload: HandlingPayload = { result: form.result, detail: form.detail.trim() }
  if (form.result === '更换车辆' && form.new_vehicle_id) {
    payload.new_vehicle_id = form.new_vehicle_id
  }
  if (form.result === '更换司机' && form.new_driver_account_id) {
    payload.new_driver_account_id = form.new_driver_account_id
  }
  if (form.result === '调整送达时间' && form.adjusted_deliver_at) {
    payload.adjusted_deliver_at = toIso(form.adjusted_deliver_at)
  }
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
</script>

<template>
  <div class="exception-page" v-loading="loading">
    <h1>运输异常处理 · {{ view?.task_no ?? '—' }}</h1>
    <template v-if="view">
      <el-card class="panel" shadow="never">
        <div class="headline">
          <span>订单号：{{ view.order_no }}</span>
          <span>异常上报：{{ view.anomalies.length }} 条</span>
          <span>处理记录：{{ view.handling_records.length }} 条</span>
        </div>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>异常处理记录（只读追加）</h2>
        <el-table :data="view.handling_records" size="small" empty-text="尚未追加处理记录">
          <el-table-column prop="result" label="处理结果" width="130" />
          <el-table-column prop="reason" label="说明 / 原因" min-width="200" />
          <el-table-column prop="actor" label="处理角色" width="100" />
          <el-table-column prop="handled_at" label="处理时间" min-width="170" />
          <el-table-column label="更换前 → 更换后" min-width="240">
            <template #default="scope">
              <template v-if="scope.row.result === '更换车辆'">
                {{ scope.row.before_vehicle_plate || '—' }} → {{ scope.row.after_vehicle_plate || '—' }}
              </template>
              <template v-else-if="scope.row.result === '更换司机'">
                {{ scope.row.before_driver_name || '—' }} → {{ scope.row.after_driver_name || '—' }}
              </template>
              <template v-else-if="scope.row.result === '调整送达时间'">
                {{ scope.row.before_deliver_at || '—' }} → {{ scope.row.after_deliver_at || '—' }}
              </template>
              <template v-else>—</template>
            </template>
          </el-table-column>
          <el-table-column prop="order_status" label="订单状态" width="110" />
        </el-table>
      </el-card>

      <el-card v-for="anomaly in view.anomalies" :key="anomaly.id" class="panel" shadow="never">
        <h2>异常 {{ anomaly.anomaly_no }} · {{ anomaly.kind }}</h2>
        <p class="detail">{{ anomaly.detail }}</p>
        <p class="muted">发生时间 {{ anomaly.occurred_at }} · 上报司机 {{ anomaly.actor }} · 现场照片 {{ anomaly.photos.join('，') }}</p>

        <el-alert
          v-if="handlingFor(anomaly.id)"
          class="notice"
          type="success"
          :closable="false"
          :title="`已处理：${handlingFor(anomaly.id)?.result}`"
        />
        <div v-else class="form">
          <label class="field">
            <span>处理结果</span>
            <el-select v-model="formFor(anomaly.id).result">
              <el-option v-for="item in results" :key="item" :label="item" :value="item" />
            </el-select>
          </label>
          <label class="field">
            <span>处理说明</span>
            <el-input v-model="formFor(anomaly.id).detail" maxlength="500" placeholder="请填写处理说明或原因" />
          </label>
          <label v-if="formFor(anomaly.id).result === '更换车辆'" class="field">
            <span>新车辆 ID</span>
            <el-input-number v-model="formFor(anomaly.id).new_vehicle_id" :min="1" controls-position="right" />
          </label>
          <label v-if="formFor(anomaly.id).result === '更换司机'" class="field">
            <span>新司机账号 ID</span>
            <el-input-number v-model="formFor(anomaly.id).new_driver_account_id" :min="1" controls-position="right" />
          </label>
          <label v-if="formFor(anomaly.id).result === '调整送达时间'" class="field">
            <span>新送达时间</span>
            <el-date-picker
              v-model="formFor(anomaly.id).adjusted_deliver_at"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              placeholder="选择新的计划送达时间"
            />
          </label>
          <el-button
            type="primary"
            :loading="busyId === anomaly.id"
            @click="onSubmit(anomaly)"
          >
            追加处理记录
          </el-button>
        </div>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.exception-page h1 { margin: 0 0 var(--space-4); font-size: var(--font-size-xl); }
.panel { margin-bottom: var(--space-4); }
.panel h2 { margin: 0 0 var(--space-3); font-size: var(--font-size-md); }
.headline { display: flex; flex-wrap: wrap; gap: var(--space-4); font-size: var(--font-size-sm); }
.detail { margin: 0 0 var(--space-2); font-size: var(--font-size-sm); }
.muted { margin: 0; color: var(--color-text-muted); font-size: var(--font-size-sm); }
.notice { margin-top: var(--space-2); }
.form { display: flex; flex-direction: column; align-items: flex-start; gap: var(--space-3); margin-top: var(--space-3); }
.field { display: flex; align-items: center; gap: var(--space-3); width: 100%; font-size: var(--font-size-sm); }
.field > span { flex-shrink: 0; width: 9em; color: var(--color-text-muted); }
</style>
