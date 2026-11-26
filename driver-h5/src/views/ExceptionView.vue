<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getDriverExceptions, submitAnomaly } from '@/api/exception'
import { getDriverTask } from '@/api/dispatch'
import H5PageHeader from '@/components/H5PageHeader.vue'
import H5Card from '@/components/H5Card.vue'
import H5Notice from '@/components/H5Notice.vue'
import H5Uploader from '@/components/H5Uploader.vue'
import H5EmptyState from '@/components/H5EmptyState.vue'
import H5BottomBar from '@/components/H5BottomBar.vue'
import type { DriverTask } from '@/types/dispatch'
import type { AnomalyKind, ExceptionView } from '@/types/exception'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.params.taskId)
const task = ref<DriverTask | null>(null)
const view = ref<ExceptionView | null>(null)
const busy = ref(false)

const kinds: { label: string; value: AnomalyKind }[] = [
  { label: '车辆故障', value: '故障' },
  { label: '事故', value: '事故' },
  { label: '封路', value: '封路' },
  { label: '拥堵', value: '拥堵' },
  { label: '货物问题', value: '货物异常' },
  { label: '预计延误', value: '预计延误' },
  { label: '其它', value: '其他' },
]
const form = ref({ kind: '故障' as AnomalyKind, detail: '', photo: '', occurred_at: '' })

function displayKind(kind: string): string {
  return kinds.find((item) => item.value === kind)?.label ?? kind
}

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function toIso(value: string): string {
  if (!value) return ''
  if (value.length === 16) return `${value}:00+00:00`
  if (value.length === 19) return `${value}+00:00`
  return value
}

function onFileChange(files: File[]): void {
  form.value.photo = files[0] ? `uploads/${files[0].name}` : ''
}

async function load(): Promise<void> {
  busy.value = true
  try {
    const [detail, records] = await Promise.all([getDriverTask(taskId), getDriverExceptions(taskId)])
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
    showToast('请选择现场照片')
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

onMounted(load)
</script>

<template>
  <div class="h5-page h5-page--with-bar">
    <H5PageHeader title="异常处理" />
    <main class="h5-scroll">
      <H5Card>
        <h2 class="ex-title">上报运输异常</h2>
        <p class="ex-sub">{{ task?.task_no }} · {{ task?.shipping.name }} → {{ task?.receiving.name }}</p>

        <label class="h5-label"><span class="h5-req">*</span>异常类型</label>
        <van-radio-group v-model="form.kind" class="ex-kinds">
          <van-radio v-for="item in kinds" :key="item.value" :name="item.value">{{ item.label }}</van-radio>
        </van-radio-group>

        <H5Uploader label="现场照片" :status="form.photo ? 'done' : 'idle'" @change="onFileChange" />
        <label class="h5-label"><span class="h5-req">*</span>异常说明</label>
        <van-field v-model="form.detail" type="textarea" rows="3" placeholder="请描述异常情况" />
        <label class="h5-label">发生时间</label>
        <van-field v-model="form.occurred_at" placeholder="YYYY-MM-DDTHH:mm" />
        <H5Notice tone="info">提交后由物流公司处置；车辆更换、司机更换等变更均由公司通过异常流程处理，司机不可自行换车。</H5Notice>
      </H5Card>

      <h2 class="h5-section-title">异常处理记录</h2>
      <H5EmptyState v-if="!view?.anomalies.length" text="暂无异常处理记录" />
      <H5Card v-for="item in view?.anomalies ?? []" :key="item.id">
        <div class="h5-row"><span class="v">{{ item.anomaly_no }}</span><span class="v">{{ displayKind(item.kind) }} · {{ stamp(item.occurred_at) }}</span></div>
        <div class="h5-row"><span class="k">处理结果</span><span class="v">—（待公司处置）</span></div>
        <p class="ex-hint">处理结果为追加记录，原上报内容保留。</p>
      </H5Card>
    </main>

    <H5BottomBar>
      <van-button block type="primary" :loading="busy" @click="onSubmit">提交异常</van-button>
    </H5BottomBar>
  </div>
</template>

<style scoped>
.ex-title { margin: 0; font-size: var(--font-size-md); font-weight: 600; }
.ex-sub { margin: var(--space-1) 0 var(--space-4); font-size: var(--font-size-xs); color: var(--color-text-3); }
.ex-kinds { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-2); padding: var(--space-2) 0; }
.ex-hint { margin: var(--space-2) 0 0; font-size: var(--font-size-xs); color: var(--color-text-3); }
</style>
