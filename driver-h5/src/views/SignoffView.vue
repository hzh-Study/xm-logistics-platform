<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getDriverTask } from '@/api/dispatch'
import { getDriverProgress } from '@/api/checkin'
import { addUnloadingAnomaly, addUnloadingPhotos, submitArrivalCheckin, submitArrivalNote, submitSignoff } from '@/api/signoff'
import H5PageHeader from '@/components/H5PageHeader.vue'
import H5Card from '@/components/H5Card.vue'
import H5Notice from '@/components/H5Notice.vue'
import H5Uploader from '@/components/H5Uploader.vue'
import H5BottomBar from '@/components/H5BottomBar.vue'
import type { DriverTask } from '@/types/dispatch'
import type { TaskProgress } from '@/types/checkin'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.params.taskId)
const task = ref<DriverTask | null>(null)
const progress = ref<TaskProgress | null>(null)
const busy = ref(false)

const phases = ['卸货前', '卸货中', '卸货完成'] as const
const anomalyKinds = [
  { label: '货物破损', value: '货损' },
  { label: '数量不符', value: '数量不符' },
  { label: '拒收', value: '拒收' },
]
const conditions = [
  { label: '完好', value: '完好' },
  { label: '破损', value: '货损' },
  { label: '数量不符', value: '数量不符' },
  { label: '其他', value: '其他' },
]

const arrivalForm = ref({ latitude: '', longitude: '', arrived_at: '', photos: [] as string[], notes: '' })
const noteText = ref('')
const photoPaths = ref<Record<string, string>>({ 卸货前: '', 卸货中: '', 卸货完成: '' })
const anomalyForm = ref({ kind: '货损', detail: '', photos: [] as string[] })
const signoffForm = ref({
  receiving_condition: '完好' as string,
  received_at: '',
  receiver_name: '',
  signature_photos: [] as string[],
  vouchers: [] as string[],
  notes: '',
})

const canArrive = computed(() => progress.value?.status === '运输中')
const canSignoff = computed(() => progress.value?.status === '待签收')
const currentArrival = computed(() => progress.value?.arrival_checkins.at(-1) ?? null)
const noteDone = computed(() => (progress.value?.arrival_notes.length ?? 0) > 0)
const anomalyPending = computed(() => currentArrival.value?.exception_note_required ?? false)
const photoDone = computed(() => {
  const done = new Set(progress.value?.unloading_photos.map((p) => p.phase) ?? [])
  return phases.every((phase) => done.has(phase))
})

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function displayKind(value: string): string {
  return anomalyKinds.find((item) => item.value === value)?.label ?? value
}

function displayCondition(value: string): string {
  return conditions.find((item) => item.value === value)?.label ?? value
}

function toIso(value: string): string {
  if (!value) return ''
  return value.length === 16 ? `${value}:00+00:00` : value
}

function locate(): void {
  if (!navigator.geolocation) {
    showToast('当前设备不支持定位，请手动填写坐标')
    return
  }
  navigator.geolocation.getCurrentPosition(
    (position) => {
      arrivalForm.value.latitude = position.coords.latitude.toFixed(6)
      arrivalForm.value.longitude = position.coords.longitude.toFixed(6)
    },
    () => showToast('定位失败，请手动填写坐标'),
  )
}

function onArrivalFiles(files: File[]): void {
  arrivalForm.value.photos = files.map((file) => `uploads/${file.name}`)
}

function onPhaseFiles(phase: string, files: File[]): void {
  photoPaths.value[phase] = files[0] ? `uploads/${files[0].name}` : ''
}

function onAnomalyFiles(files: File[]): void {
  anomalyForm.value.photos = files.map((file) => `uploads/${file.name}`)
}

function onSignatureFiles(files: File[]): void {
  signoffForm.value.signature_photos = files.map((file) => `uploads/${file.name}`)
}

function onVoucherFiles(files: File[]): void {
  signoffForm.value.vouchers = files.map((file) => `uploads/${file.name}`)
}

async function load(): Promise<void> {
  busy.value = true
  try {
    const [detail, view] = await Promise.all([getDriverTask(taskId), getDriverProgress(taskId)])
    task.value = detail
    progress.value = view
  } catch (error) {
    showToast(error instanceof Error ? error.message : '读取任务失败')
  } finally {
    busy.value = false
  }
}

async function onArrival(): Promise<void> {
  const form = arrivalForm.value
  const lat = Number(form.latitude)
  const lon = Number(form.longitude)
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    showToast('请先获取或填写定位坐标')
    return
  }
  if (!form.photos.length) {
    showToast('请选择现场照片')
    return
  }
  busy.value = true
  try {
    const result = await submitArrivalCheckin(taskId, {
      latitude: lat,
      longitude: lon,
      arrived_at: toIso(form.arrived_at) || new Date().toISOString(),
      photos: form.photos,
      notes: form.notes,
    })
    showToast(result.exception_note_required ? '位置异常：请提交异常说明' : '收货地打卡成功')
    await load()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '打卡失败')
  } finally {
    busy.value = false
  }
}

async function onNote(): Promise<void> {
  if (!noteText.value.trim()) {
    showToast('请填写位置异常说明')
    return
  }
  busy.value = true
  try {
    await submitArrivalNote(taskId, noteText.value.trim())
    showToast('异常说明已提交')
    noteText.value = ''
    await load()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '提交失败')
  } finally {
    busy.value = false
  }
}

async function onPhoto(phase: (typeof phases)[number]): Promise<void> {
  const path = photoPaths.value[phase]?.trim()
  if (!path) {
    showToast('请选择照片')
    return
  }
  busy.value = true
  try {
    await addUnloadingPhotos(taskId, phase, [path])
    showToast(`${phase}照片已上传`)
    photoPaths.value[phase] = ''
    await load()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '上传失败')
  } finally {
    busy.value = false
  }
}

async function onAnomaly(): Promise<void> {
  const form = anomalyForm.value
  if (!form.detail.trim()) {
    showToast('请填写卸货异常详情')
    return
  }
  busy.value = true
  try {
    await addUnloadingAnomaly(taskId, form.kind, form.detail.trim(), form.photos)
    showToast('卸货异常已上报')
    anomalyForm.value = { kind: '货损', detail: '', photos: [] }
    await load()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '上报失败')
  } finally {
    busy.value = false
  }
}

async function onSignoff(): Promise<void> {
  const form = signoffForm.value
  if (!photoDone.value) {
    showToast('请先上传三阶段卸货照片')
    return
  }
  if (anomalyPending.value && !noteDone.value) {
    showToast('位置异常须先提交异常说明')
    return
  }
  if (!form.receiver_name.trim() || !form.signature_photos.length || !form.vouchers.length) {
    showToast('请填写收货人并选择签收照片与凭证')
    return
  }
  busy.value = true
  try {
    await submitSignoff(taskId, {
      receiving_condition: form.receiving_condition,
      received_at: toIso(form.received_at) || new Date().toISOString(),
      receiver_name: form.receiver_name.trim(),
      signature_photos: form.signature_photos,
      vouchers: form.vouchers,
      notes: form.notes,
    })
    showToast('签收资料已提交，等待公司确认完成')
    await router.replace('/tasks')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '提交失败')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="h5-page h5-page--with-bar">
    <H5PageHeader title="签收" />
    <main class="h5-scroll">
      <H5Card>
        <h2 class="sg-title">收货信息</h2>
        <div class="h5-row"><span class="k">任务编号</span><span class="v h5-num">{{ task?.task_no }}</span></div>
        <div class="h5-row"><span class="k">收货快照</span><span class="v">{{ task?.receiving.name }} · {{ task?.receiving.detail_address }}</span></div>
        <div class="h5-row"><span class="k">收货人</span><span class="v">{{ task?.receiving.contact }} · {{ task?.receiving.phone }}</span></div>
        <div class="h5-row"><span class="k">计划送达</span><span class="v h5-num">{{ stamp(task?.planned_deliver_at ?? '') }}</span></div>
        <div class="h5-row"><span class="k">当前状态</span><span class="v">{{ progress?.status || '—' }}</span></div>
      </H5Card>

      <H5Card>
        <h2 class="sg-title">收货地打卡</h2>
        <div class="h5-map">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s7-6 7-11a7 7 0 1 0-14 0c0 5 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></svg>
          <span>收货地定位区（原型占位）</span>
        </div>
        <div class="h5-row" v-if="currentArrival">
          <span class="k">距离快照</span><span class="v">{{ currentArrival.distance_m ?? '—' }} 米 · {{ currentArrival.position_status }}</span>
        </div>
        <template v-if="canArrive && !currentArrival">
          <van-button block size="small" @click="locate">获取当前位置</van-button>
          <label class="h5-label">纬度</label><van-field v-model="arrivalForm.latitude" placeholder="请输入纬度" />
          <label class="h5-label">经度</label><van-field v-model="arrivalForm.longitude" placeholder="请输入经度" />
          <label class="h5-label">到达时间</label><van-field v-model="arrivalForm.arrived_at" placeholder="YYYY-MM-DDTHH:mm" />
          <H5Uploader label="现场照片" multiple :status="arrivalForm.photos.length ? 'done' : 'idle'" @change="onArrivalFiles" />
          <label class="h5-label">备注</label><van-field v-model="arrivalForm.notes" type="textarea" rows="2" />
          <div class="sg-action"><van-button block type="primary" :loading="busy" @click="onArrival">提交打卡</van-button></div>
        </template>
        <H5Notice v-if="currentArrival?.warning" tone="warning">{{ currentArrival.warning }}</H5Notice>
      </H5Card>

      <H5Card v-if="anomalyPending && !noteDone">
        <h2 class="sg-title">位置异常说明</h2>
        <H5Notice tone="warning">位置异常不会自动驳回，但提交签收资料前须提交说明。</H5Notice>
        <label class="h5-label"><span class="h5-req">*</span>异常说明</label>
        <van-field v-model="noteText" type="textarea" rows="2" />
        <div class="sg-action"><van-button block type="primary" :loading="busy" @click="onNote">提交说明</van-button></div>
      </H5Card>

      <H5Card>
        <h2 class="sg-title">卸货与签收资料</h2>
        <div v-for="phase in phases" :key="phase" class="sg-phase">
          <span>{{ phase }}</span>
          <H5Uploader :label="phase" :status="photoPaths[phase] ? 'done' : 'idle'" @change="(files) => onPhaseFiles(phase, files)" />
          <van-button v-if="photoPaths[phase]" size="small" type="primary" :loading="busy" @click="onPhoto(phase)">上传</van-button>
        </div>
        <p class="sg-hint">{{ photoDone ? '三阶段照片已齐' : '请上传卸货前 / 中 / 后照片' }}</p>

        <h3 class="sg-subtitle">卸货异常（如有）</h3>
        <van-radio-group v-model="anomalyForm.kind" class="sg-kinds">
          <van-radio v-for="item in anomalyKinds" :key="item.value" :name="item.value">{{ item.label }}</van-radio>
        </van-radio-group>
        <label class="h5-label">异常详情</label><van-field v-model="anomalyForm.detail" type="textarea" rows="2" />
        <H5Uploader label="异常照片" multiple :status="anomalyForm.photos.length ? 'done' : 'idle'" @change="onAnomalyFiles" />
        <div class="sg-action"><van-button block size="small" :loading="busy" @click="onAnomaly">上报异常</van-button></div>
        <p v-for="item in progress?.unloading_anomalies ?? []" :key="item.id" class="sg-log">{{ displayKind(item.kind) }} · {{ item.detail }}</p>

        <h3 class="sg-subtitle">签收资料</h3>
        <label class="h5-label">收货状况</label>
        <van-radio-group v-model="signoffForm.receiving_condition" class="sg-kinds">
          <van-radio v-for="item in conditions" :key="item.value" :name="item.value">{{ item.label }}</van-radio>
        </van-radio-group>
        <label class="h5-label"><span class="h5-req">*</span>签收人</label><van-field v-model="signoffForm.receiver_name" />
        <label class="h5-label">签收时间</label><van-field v-model="signoffForm.received_at" placeholder="YYYY-MM-DDTHH:mm" />
        <H5Uploader label="签收照片" multiple :status="signoffForm.signature_photos.length ? 'done' : 'idle'" @change="onSignatureFiles" />
        <H5Uploader label="签收凭证" multiple :status="signoffForm.vouchers.length ? 'done' : 'idle'" @change="onVoucherFiles" />
        <label class="h5-label">备注</label><van-field v-model="signoffForm.notes" type="textarea" rows="2" />
        <p v-if="progress?.signoff_voucher" class="sg-done">已提交凭证 {{ progress.signoff_voucher.voucher_no }} · {{ displayCondition(progress.signoff_voucher.receiving_condition) }}</p>
      </H5Card>
    </main>

    <H5BottomBar>
      <van-button block type="primary" :loading="busy" @click="onSignoff">确认签收</van-button>
    </H5BottomBar>
  </div>
</template>

<style scoped>
.sg-title { margin: 0; font-size: var(--font-size-md); font-weight: 600; }
.sg-subtitle { margin: var(--space-4) 0 var(--space-2); font-size: var(--font-size-sm); font-weight: 600; }
.sg-action { margin-top: var(--space-3); }
.sg-phase { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.sg-phase > span { flex: 0 0 4em; font-size: var(--font-size-sm); color: var(--color-text-2); }
.sg-phase :deep(.h5-uploader__label) { display: none; }
.sg-hint { margin: var(--space-2) 0; font-size: var(--font-size-xs); color: var(--color-text-3); }
.sg-kinds { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-2); padding: var(--space-2) 0; }
.sg-log { margin: var(--space-2) 0 0; font-size: var(--font-size-xs); color: var(--color-text-2); }
.sg-done { margin: var(--space-3) 0 0; font-size: var(--font-size-sm); color: var(--color-success); }
</style>
