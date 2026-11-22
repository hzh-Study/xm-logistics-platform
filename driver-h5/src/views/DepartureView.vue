<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getDriverTask } from '@/api/dispatch'
import {
  addLoadingAnomaly,
  addLoadingPhotos,
  getDriverProgress,
  startTransport,
  submitCheckin,
  submitExceptionNote,
} from '@/api/checkin'
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
const anomalyKinds = ['数量不符', '货损', '超载'] as const

const checkinForm = ref({ latitude: '', longitude: '', arrived_at: '', photo: '', notes: '' })
const noteText = ref('')
const photoPaths = ref<Record<string, string>>({ 装货前: '', 装货中: '', 装货完成: '' })
const anomalyForm = ref({ kind: '数量不符' as (typeof anomalyKinds)[number], detail: '', photo: '' })
const startForm = ref({ cargo_confirmed: false, vehicle_confirmed: false, notes: '' })

const hasCheckin = computed(() => (progress.value?.checkins.length ?? 0) > 0)
const photoDone = computed(() => {
  const done = new Set(progress.value?.loading_photos.map((p) => p.phase) ?? [])
  return phases.every((phase) => done.has(phase))
})
const noteDone = computed(() => (progress.value?.exception_notes.length ?? 0) > 0)
const currentCheckin = computed(() => progress.value?.checkins.at(-1) ?? null)
const anomalyPending = computed(() => currentCheckin.value?.exception_note_required ?? false)

onMounted(load)

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

function toIso(value: string): string {
  if (!value) return ''
  return value.length === 16 ? `${value}:00+00:00` : value
}

async function onCheckin(): Promise<void> {
  const form = checkinForm.value
  const lat = Number(form.latitude)
  const lon = Number(form.longitude)
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    showToast('请先获取或填写定位坐标')
    return
  }
  if (!form.photo.trim()) {
    showToast('请填写现场照片相对路径')
    return
  }
  busy.value = true
  try {
    const result = await submitCheckin(taskId, {
      latitude: lat,
      longitude: lon,
      arrived_at: toIso(form.arrived_at) || new Date().toISOString(),
      photos: [form.photo.trim()],
      notes: form.notes,
    })
    lastWarning.value = result.warning
    if (result.exception_note_required) {
      showToast('位置异常：请提交异常说明后可起运')
    } else {
      showToast('发货地打卡成功')
    }
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
    showToast('请填写照片相对路径')
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
    await addLoadingAnomaly(taskId, form.kind, form.detail.trim(), form.photo.trim() ? [form.photo.trim()] : [])
    showToast('装货异常已上报')
    anomalyForm.value = { kind: '数量不符', detail: '', photo: '' }
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
</script>

<template>
  <div class="departure-page">
    <header class="topbar">
      <button class="back" type="button" @click="router.replace('/tasks')">返回</button>
      <span>发货地打卡与起运</span>
      <span class="state">{{ progress?.status ?? '—' }}</span>
    </header>

    <main class="body">
      <p v-if="!task" class="empty">加载中…</p>
      <template v-else>
        <section class="card">
          <h2>任务信息</h2>
          <div class="row"><span>任务号</span><span>{{ task.task_no }}</span></div>
          <div class="row"><span>货物</span><span>{{ task.cargo_name }}</span></div>
          <div class="row"><span>发货地</span><span>{{ task.shipping.name }}</span></div>
          <div class="row"><span>详细地址</span><span>{{ task.shipping.detail_address }}</span></div>
          <div class="row"><span>计划装货</span><span>{{ task.planned_load_at }}</span></div>
        </section>

        <section class="card">
          <h2>1. 发货地打卡</h2>
          <p v-if="currentCheckin" class="done">已打卡 · {{ currentCheckin.position_status }}</p>
          <template v-if="!hasCheckin">
            <button class="btn ghost" type="button" @click="locate">获取当前位置</button>
            <label class="field"><span>纬度</span><input v-model="checkinForm.latitude" inputmode="decimal" /></label>
            <label class="field"><span>经度</span><input v-model="checkinForm.longitude" inputmode="decimal" /></label>
            <label class="field"><span>到达时间</span><input v-model="checkinForm.arrived_at" type="datetime-local" /></label>
            <label class="field"><span>现场照片（相对路径）</span><input v-model="checkinForm.photo" /></label>
            <label class="field"><span>备注</span><input v-model="checkinForm.notes" /></label>
            <button class="btn primary" type="button" :disabled="busy" @click="onCheckin">提交打卡</button>
          </template>
          <p v-if="lastWarning || currentCheckin?.warning" class="warn">
            {{ lastWarning || currentCheckin?.warning }}
          </p>
        </section>

        <section v-if="anomalyPending && !noteDone" class="card">
          <h2>位置异常说明</h2>
          <p class="warn">位置异常不会自动驳回，但起运前须提交说明。</p>
          <label class="field"><span>异常说明</span><input v-model="noteText" /></label>
          <button class="btn primary" type="button" :disabled="busy" @click="onNote">提交说明</button>
        </section>

        <section class="card">
          <h2>2. 装货照片</h2>
          <div v-for="phase in phases" :key="phase" class="photo-row">
            <span class="phase">{{ phase }}</span>
            <input v-model="photoPaths[phase]" :placeholder="`${phase}照片相对路径`" />
            <button class="btn small" type="button" :disabled="busy" @click="onPhoto(phase)">上传</button>
          </div>
          <p class="hint">{{ photoDone ? '三阶段照片已齐' : '请依次上传装货前 / 中 / 完成照片' }}</p>
        </section>

        <section class="card">
          <h2>3. 装货异常</h2>
          <label class="field">
            <span>异常类型</span>
            <select v-model="anomalyForm.kind">
              <option v-for="kind in anomalyKinds" :key="kind" :value="kind">{{ kind }}</option>
            </select>
          </label>
          <label class="field"><span>详情</span><input v-model="anomalyForm.detail" /></label>
          <label class="field"><span>照片（相对路径）</span><input v-model="anomalyForm.photo" /></label>
          <button class="btn ghost" type="button" :disabled="busy" @click="onAnomaly">上报异常</button>
          <p v-for="item in progress?.loading_anomalies ?? []" :key="item.id" class="log">
            {{ item.kind }} · {{ item.detail }}
          </p>
        </section>

        <section class="card">
          <h2>4. 货物与车辆确认</h2>
          <label class="check"><input v-model="startForm.cargo_confirmed" type="checkbox" /> 货物已核对</label>
          <label class="check"><input v-model="startForm.vehicle_confirmed" type="checkbox" /> 车辆已核对</label>
          <label class="field"><span>起运备注</span><input v-model="startForm.notes" /></label>
          <button class="btn primary" type="button" :disabled="busy || progress?.status === '运输中'" @click="onStart">
            开始运输
          </button>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.departure-page { display: flex; flex-direction: column; min-height: 100vh; }
.topbar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); padding: var(--space-4); background: var(--color-surface); border-bottom: 1px solid var(--color-border); font-size: var(--font-size-md); }
.back { min-height: var(--tap-min); padding: 0 var(--space-2); font: inherit; color: var(--color-text); background: transparent; border: 0; }
.state { font-size: var(--font-size-sm); color: var(--color-accent); }
.body { flex: 1; padding: var(--space-4); }
.empty { padding: var(--space-8) var(--space-4); text-align: center; color: var(--color-text-muted); }
.card { margin-bottom: var(--space-3); padding: var(--space-4); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius); }
.card h2 { margin: 0 0 var(--space-3); font-size: var(--font-size-md); }
.row { display: flex; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-2); font-size: var(--font-size-sm); }
.row > span:first-child { flex-shrink: 0; color: var(--color-text-muted); }
.row > span:last-child { text-align: right; }
.field { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); font-size: var(--font-size-sm); }
.field > span { flex-shrink: 0; width: 7em; color: var(--color-text-muted); }
.field input, .field select, .photo-row input { flex: 1; min-width: 0; min-height: var(--tap-min); padding: 0 var(--space-2); font: inherit; color: var(--color-text); background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius); }
.photo-row { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.phase { flex-shrink: 0; width: 4em; font-size: var(--font-size-sm); color: var(--color-text-muted); }
.check { display: flex; align-items: center; gap: var(--space-2); min-height: var(--tap-min); font-size: var(--font-size-sm); }
.btn { min-height: var(--tap-min); padding: 0 var(--space-4); font: inherit; border-radius: var(--radius); cursor: pointer; }
.btn.primary { color: #fff; background: var(--color-accent); border: 1px solid var(--color-accent); }
.btn.ghost { color: var(--color-text); background: var(--color-surface); border: 1px solid var(--color-border); }
.btn.small { padding: 0 var(--space-3); }
.btn:disabled { opacity: 0.6; cursor: default; }
.done { margin: 0 0 var(--space-2); font-size: var(--font-size-sm); color: var(--color-success); }
.warn { margin: var(--space-2) 0; font-size: var(--font-size-sm); color: var(--color-warning); }
.hint { margin: var(--space-2) 0 0; font-size: var(--font-size-sm); color: var(--color-text-muted); }
.log { margin: var(--space-2) 0 0; font-size: var(--font-size-sm); color: var(--color-text-muted); }
</style>
