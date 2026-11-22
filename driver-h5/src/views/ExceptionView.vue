<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getDriverExceptions, submitAnomaly } from '@/api/exception'
import { getDriverTask } from '@/api/dispatch'
import type { DriverTask } from '@/types/dispatch'
import type { AnomalyKind, ExceptionView } from '@/types/exception'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.params.taskId)
const task = ref<DriverTask | null>(null)
const view = ref<ExceptionView | null>(null)
const busy = ref(false)

const kinds: AnomalyKind[] = ['故障', '事故', '封路', '拥堵', '货物异常', '预计延误', '其他']
const form = ref({ kind: '故障' as AnomalyKind, detail: '', photo: '', occurred_at: '' })

function toIso(value: string): string {
  if (!value) return ''
  if (value.length === 16) return `${value}:00+00:00`
  if (value.length === 19) return `${value}+00:00`
  return value
}

onMounted(load)

async function load(): Promise<void> {
  busy.value = true
  try {
    const [detail, records] = await Promise.all([
      getDriverTask(taskId),
      getDriverExceptions(taskId),
    ])
    task.value = detail
    view.value = records
  } catch (error) {
    showToast(error instanceof Error ? error.message : '读取异常记录失败')
  } finally {
    busy.value = false
  }
}

async function onSubmit(): Promise<void> {
  const current = form.value
  if (!current.detail.trim()) {
    showToast('请填写异常说明')
    return
  }
  if (!current.photo.trim()) {
    showToast('请填写现场照片相对路径')
    return
  }
  busy.value = true
  try {
    await submitAnomaly(taskId, {
      kind: current.kind,
      detail: current.detail.trim(),
      photos: [current.photo.trim()],
      occurred_at: toIso(current.occurred_at) || new Date().toISOString(),
    })
    showToast('在途异常已上报，请等待公司处理')
    form.value = { kind: '故障', detail: '', photo: '', occurred_at: '' }
    await load()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '上报失败')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="exception-page">
    <header class="topbar">
      <button class="back" type="button" @click="router.replace('/tasks')">返回</button>
      <span>在途异常上报</span>
      <span class="state">{{ task?.status ?? '—' }}</span>
    </header>

    <main class="body">
      <p v-if="!task" class="empty">加载中…</p>
      <template v-else>
        <section class="card">
          <h2>任务信息</h2>
          <div class="row"><span>任务号</span><span>{{ task.task_no }}</span></div>
          <div class="row"><span>车牌</span><span>{{ task.vehicle_plate }}</span></div>
          <div class="row"><span>计划送达</span><span>{{ task.planned_deliver_at }}</span></div>
        </section>

        <section class="card">
          <h2>上报在途异常</h2>
          <p class="hint">故障、事故、封路、拥堵、货物异常、预计延误等均可上报，请附现场照片。</p>
          <label class="field">
            <span>异常类型</span>
            <select v-model="form.kind">
              <option v-for="kind in kinds" :key="kind" :value="kind">{{ kind }}</option>
            </select>
          </label>
          <label class="field"><span>异常说明</span><input v-model="form.detail" maxlength="500" /></label>
          <label class="field"><span>现场照片</span><input v-model="form.photo" placeholder="照片相对路径" /></label>
          <label class="field"><span>发生时间</span><input v-model="form.occurred_at" type="datetime-local" /></label>
          <button class="btn primary" type="button" :disabled="busy" @click="onSubmit">提交异常</button>
        </section>

        <section class="card">
          <h2>异常处理结果</h2>
          <p v-if="!view?.handling_records.length" class="hint">公司尚未处理上报的异常。</p>
          <div v-for="record in view?.handling_records ?? []" :key="record.id" class="log">
            <p class="result">{{ record.result }}</p>
            <p class="muted">{{ record.reason || '—' }}</p>
            <p class="meta">处理角色 {{ record.actor }} · 处理时间 {{ record.handled_at }}</p>
          </div>
        </section>

        <section class="card">
          <h2>异常上报记录</h2>
          <p v-if="!view?.anomalies.length" class="hint">暂无在途异常上报。</p>
          <div v-for="anomaly in view?.anomalies ?? []" :key="anomaly.id" class="log">
            <p class="result">{{ anomaly.kind }} · {{ anomaly.detail }}</p>
            <p class="meta">{{ anomaly.occurred_at }} · {{ anomaly.photos.join('，') }}</p>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.exception-page { display: flex; flex-direction: column; min-height: 100vh; }
.topbar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); padding: var(--space-4); background: var(--color-surface); border-bottom: 1px solid var(--color-border); font-size: var(--font-size-md); }
.back { min-height: var(--tap-min); padding: 0 var(--space-2); font: inherit; color: var(--color-text); background: transparent; border: 0; }
.state { font-size: var(--font-size-sm); color: var(--color-accent); }
.body { flex: 1; padding: var(--space-4); }
.empty { padding: var(--space-8) var(--space-4); text-align: center; color: var(--color-text-muted); }
.card { margin-bottom: var(--space-3); padding: var(--space-4); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius); }
.card h2 { margin: 0 0 var(--space-3); font-size: var(--font-size-md); }
.row { display: flex; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-2); font-size: var(--font-size-sm); }
.row > span:first-child { flex-shrink: 0; color: var(--color-text-muted); }
.field { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); font-size: var(--font-size-sm); }
.field > span { flex-shrink: 0; width: 6em; color: var(--color-text-muted); }
.field input, .field select { flex: 1; min-width: 0; min-height: var(--tap-min); padding: 0 var(--space-2); font: inherit; color: var(--color-text); background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius); }
.btn { min-height: var(--tap-min); padding: 0 var(--space-4); font: inherit; border-radius: var(--radius); cursor: pointer; }
.btn.primary { color: #fff; background: var(--color-accent); border: 1px solid var(--color-accent); }
.btn:disabled { opacity: 0.6; cursor: default; }
.hint { margin: 0 0 var(--space-3); font-size: var(--font-size-sm); color: var(--color-text-muted); }
.log { margin-top: var(--space-3); padding-top: var(--space-3); border-top: 1px solid var(--color-border); }
.result { margin: 0 0 var(--space-1); font-size: var(--font-size-sm); font-weight: 600; }
.meta { margin: var(--space-1) 0 0; font-size: var(--font-size-sm); color: var(--color-text-muted); }
.muted { margin: var(--space-1) 0 0; font-size: var(--font-size-sm); color: var(--color-text-muted); }
</style>
