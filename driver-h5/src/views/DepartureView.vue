<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getDriverTask } from '@/api/dispatch'
import { addLoadingAnomaly, addLoadingPhotos, getDriverProgress, startTransport, submitCheckin, submitExceptionNote } from '@/api/checkin'
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
const lastWarning = ref('')

const phases = ['装货前', '装货中', '装货完成'] as const
const anomalyKinds = [
  { label: '数量不符', value: '数量不符' },
  { label: '货物破损', value: '货损' },
  { label: '描述不符', value: '数量不符' },
  { label: '无法装货', value: '货损' },
  { label: '超载', value: '超载' },
  { label: '其它', value: '货损' },
]

const checkinForm = ref({ latitude: '', longitude: '', arrived_at: '', photos: [] as string[], notes: '' })
const noteText = ref('')
const photoPaths = ref<Record<string, string>>({ 装货前: '', 装货中: '', 装货完成: '' })
const anomalyForm = ref({ kind: '数量不符', detail: '', photos: [] as string[] })
const startForm = ref({ cargo_confirmed: false, vehicle_confirmed: false, notes: '' })

const hasCheckin = computed(() => (progress.value?.checkins.length ?? 0) > 0)
const photoDone = computed(() => {
  const done = new Set(progress.value?.loading_photos.map((p) => p.phase) ?? [])
  return phases.every((phase) => done.has(phase))
})
const noteDone = computed(() => (progress.value?.exception_notes.length ?? 0) > 0)
const currentCheckin = computed(() => progress.value?.checkins.at(-1) ?? null)
const anomalyPending = computed(() => currentCheckin.value?.exception_note_required ?? false)
const locationText = computed(() => {
  const s = task.value?.shipping
  return s ? [s.province, s.city, s.district, s.detail_address].join('') : '—'
})

function displayKind(value: string): string {
  return anomalyKinds.find((item) => item.value === value)?.label ?? value
}

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
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
      checkinForm.value.latitude = position.coords.latitude.toFixed(6)
      checkinForm.value.longitude = position.coords.longitude.toFixed(6)
    },
    () => showToast('定位失败，请手动填写坐标'),
  )
}

function onCheckinFiles(files: File[]): void {
  checkinForm.value.photos = files.map((file) => `uploads/${file.name}`)
}

function onPhaseFiles(phase: string, files: File[]): void {
  photoPaths.value[phase] = files[0] ? `uploads/${files[0].name}` : ''
}

function onAnomalyFiles(files: File[]): void {
  anomalyForm.value.photos = files.map((file) => `uploads/${file.name}`)
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

async function onCheckin(): Promise<void> {
  const form = checkinForm.value
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
    const result = await submitCheckin(taskId, {
      latitude: lat,
      longitude: lon,
      arrived_at: toIso(form.arrived_at) || new Date().toISOString(),
      photos: form.photos,
      notes: form.notes,
    })
    lastWarning.value = result.warning
    showToast(result.exception_note_required ? '位置异常：请填写异常说明后提交' : '发货地打卡成功')
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
    await submitExceptionNote(taskId, noteText.value.trim())
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
    await addLoadingPhotos(taskId, phase, [path])
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
    showToast('请填写装货异常详情')
    return
  }
  busy.value = true
  try {
    await addLoadingAnomaly(taskId, form.kind, form.detail.trim(), form.photos)
    showToast('装货异常已上报')
    anomalyForm.value = { kind: '数量不符', detail: '', photos: [] }
    await load()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '上报失败')
  } finally {
    busy.value = false
  }
}

async function onStart(): Promise<void> {
  if (!hasCheckin.value || !photoDone.value) {
    showToast('请先完成打卡与三阶段装货照片')
    return
  }
  if (anomalyPending.value && !noteDone.value) {
    showToast('位置异常须先提交异常说明')
    return
  }
  busy.value = true
  try {
    await startTransport(taskId, { ...startForm.value })
    showToast('已起运，任务进入运输中')
    await router.replace('/tasks')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '起运失败')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="h5-page h5-page--with-bar">
    <H5PageHeader title="起运 / 装货打卡" />
    <main class="h5-scroll">
      <H5Card>
        <h2 class="dp-title">发货地打卡</h2>
        <p class="dp-sub">{{ task?.task_no }} · {{ task?.shipping.name }}</p>
        <div class="h5-map">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s7-6 7-11a7 7 0 1 0-14 0c0 5 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></svg>
          <span>地图定位区（原型占位，不渲染真实地图）</span>
        </div>
        <div class="h5-row"><span class="k">定位</span><span class="v">{{ locationText }}</span></div>
        <div class="h5-row" v-if="currentCheckin">
          <span class="k">距离快照</span>
          <span class="v">{{ currentCheckin.distance_m ?? '—' }} 米 · {{ currentCheckin.position_status }}</span>
        </div>
        <div class="h5-row" v-if="currentCheckin"><span class="k">打卡时间</span><span class="v h5-num">{{ stamp(currentCheckin.arrived_at) }}</span></div>

        <template v-if="!hasCheckin">
          <van-button block size="small" @click="locate">获取当前位置</van-button>
          <label class="h5-label">纬度</label><van-field v-model="checkinForm.latitude" placeholder="请输入纬度" />
          <label class="h5-label">经度</label><van-field v-model="checkinForm.longitude" placeholder="请输入经度" />
          <label class="h5-label">打卡时间</label><van-field v-model="checkinForm.arrived_at" placeholder="YYYY-MM-DDTHH:mm" />
          <H5Uploader label="现场照片" multiple :status="checkinForm.photos.length ? 'done' : 'idle'" @change="onCheckinFiles" />
          <label class="h5-label">备注</label><van-field v-model="checkinForm.notes" type="textarea" rows="2" />
          <div class="dp-action"><van-button block type="primary" :loading="busy" @click="onCheckin">提交打卡</van-button></div>
        </template>

        <H5Notice v-if="lastWarning || currentCheckin?.warning" tone="warning">
          {{ lastWarning || currentCheckin?.warning }}
        </H5Notice>
      </H5Card>

      <H5Card v-if="anomalyPending && !noteDone">
        <h2 class="dp-title">位置异常说明</h2>
        <H5Notice tone="warning">当前位置超出允许范围，请填写异常说明后提交。位置异常不自动拒绝打卡。</H5Notice>
        <label class="h5-label"><span class="h5-req">*</span>异常说明</label>
        <van-field v-model="noteText" type="textarea" rows="2" placeholder="请说明位置异常原因" />
        <div class="dp-action"><van-button block type="primary" :loading="busy" @click="onNote">提交说明</van-button></div>
      </H5Card>

      <H5Card>
        <h2 class="dp-title">装货照片</h2>
        <p class="dp-sub">三阶段均需上传</p>
        <div v-for="phase in phases" :key="phase" class="dp-phase">
          <span>{{ phase }}</span>
          <H5Uploader :label="phase" :status="photoPaths[phase] ? 'done' : 'idle'" @change="(files) => onPhaseFiles(phase, files)" />
          <van-button v-if="photoPaths[phase]" size="small" type="primary" :loading="busy" @click="onPhoto(phase)">上传</van-button>
        </div>
        <p class="dp-hint">{{ photoDone ? '三阶段照片已齐' : '请依次上传装货前 / 装货中 / 装货完成照片' }}</p>
      </H5Card>

      <H5Card>
        <h2 class="dp-title">装货异常（如有）</h2>
        <van-radio-group v-model="anomalyForm.kind" class="dp-kinds">
          <van-radio v-for="item in anomalyKinds" :key="item.label" :name="item.value">{{ item.label }}</van-radio>
        </van-radio-group>
        <label class="h5-label">异常描述</label><van-field v-model="anomalyForm.detail" type="textarea" rows="2" />
        <H5Uploader label="异常照片" multiple :status="anomalyForm.photos.length ? 'done' : 'idle'" @change="onAnomalyFiles" />
        <div class="dp-action"><van-button block size="small" :loading="busy" @click="onAnomaly">上报异常</van-button></div>
        <p v-for="item in progress?.loading_anomalies ?? []" :key="item.id" class="dp-log">{{ displayKind(item.kind) }} · {{ item.detail }}</p>
      </H5Card>

      <H5Card>
        <h2 class="dp-title">车辆与货物确认</h2>
        <div class="h5-row"><span class="k">车辆</span><span class="v">{{ task?.vehicle_plate }} · {{ task?.vehicle_type_actual }}</span></div>
        <van-checkbox v-model="startForm.cargo_confirmed" shape="square">已核对货物</van-checkbox>
        <van-checkbox v-model="startForm.vehicle_confirmed" shape="square">已核对车辆</van-checkbox>
        <label class="h5-label">备注</label><van-field v-model="startForm.notes" type="textarea" rows="2" />
      </H5Card>
    </main>

    <H5BottomBar>
      <van-button block type="primary" :loading="busy" @click="onStart">确认装货完成并起运</van-button>
    </H5BottomBar>
  </div>
</template>

<style scoped>
.dp-title { margin: 0; font-size: var(--font-size-md); font-weight: 600; }
.dp-sub { margin: var(--space-1) 0 var(--space-3); font-size: var(--font-size-xs); color: var(--color-text-3); }
.dp-action { margin-top: var(--space-3); }
.dp-phase { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.dp-phase > span { flex: 0 0 4em; font-size: var(--font-size-sm); color: var(--color-text-2); }
.dp-phase :deep(.h5-uploader__label) { display: none; }
.dp-hint { margin: var(--space-2) 0 0; font-size: var(--font-size-xs); color: var(--color-text-3); }
.dp-kinds { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-2); padding: var(--space-2) 0; }
.dp-log { margin: var(--space-2) 0 0; font-size: var(--font-size-xs); color: var(--color-text-2); }
</style>
