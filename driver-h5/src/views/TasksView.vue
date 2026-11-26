<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { acceptTask, listDriverTasks, rejectTask } from '@/api/dispatch'
import H5PageHeader from '@/components/H5PageHeader.vue'
import H5Card from '@/components/H5Card.vue'
import H5EmptyState from '@/components/H5EmptyState.vue'
import H5BottomBar from '@/components/H5BottomBar.vue'
import type { DriverTask } from '@/types/dispatch'

const router = useRouter()
const tasks = ref<DriverTask[]>([])
const loading = ref(false)
const activeTab = ref(0)
const expanded = ref<number | null>(null)
const rejectTarget = ref<DriverTask | null>(null)
const rejectReason = ref('')
const rejectError = ref('')
const rejectOpen = ref(false)
const busy = ref(false)

const tabs = ['待确认', '进行中', '已完成'] as const

const filtered = computed(() => {
  const group = tabs[activeTab.value]
  return tasks.value.filter((task) => {
    if (group === '待确认') return task.status === '待司机确认'
    if (group === '进行中') return ['待装货', '运输中', '待签收', '待确认完成', '异常'].includes(task.status)
    return ['已完成', '已拒绝'].includes(task.status)
  })
})

const emptyText = computed(() => activeTab.value === 2 ? '暂无已完成的运输任务' : '暂无该状态的运输任务')

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function tone(status: string): string {
  if (['运输中', '待签收', '待确认完成', '已完成'].includes(status)) return 'brand'
  if (status === '异常' || status === '已拒绝') return 'error'
  return 'warning'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    tasks.value = await listDriverTasks()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '读取任务失败')
  } finally {
    loading.value = false
  }
}

function toggle(id: number): void {
  expanded.value = expanded.value === id ? null : id
}

async function onAccept(task: DriverTask): Promise<void> {
  busy.value = true
  try {
    const updated = await acceptTask(task.task_id)
    tasks.value = tasks.value.map((row) => (row.task_id === updated.task_id ? updated : row))
    showToast('已确认，任务进入待装货')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '确认失败')
  } finally {
    busy.value = false
  }
}

function openReject(task: DriverTask): void {
  rejectTarget.value = task
  rejectReason.value = ''
  rejectError.value = ''
  rejectOpen.value = true
}

async function onReject(): Promise<void> {
  const task = rejectTarget.value
  if (!task) return
  if (!rejectReason.value.trim()) {
    rejectError.value = '拒绝原因为必填项，请说明拒绝理由。'
    return
  }
  busy.value = true
  try {
    const updated = await rejectTask(task.task_id, rejectReason.value.trim())
    tasks.value = tasks.value.map((row) => (row.task_id === updated.task_id ? updated : row))
    rejectOpen.value = false
    showToast('已拒绝该任务')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '拒绝失败')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="h5-page h5-page--with-bar">
    <H5PageHeader title="我的任务" :show-back="false" />
    <main class="h5-scroll">
      <van-tabs v-model:active="activeTab" color="var(--color-accent)" title-active-color="var(--color-accent)">
        <van-tab v-for="tab in tabs" :key="tab" :title="tab" />
      </van-tabs>

      <H5EmptyState v-if="!filtered.length" :text="emptyText" />
      <H5Card v-for="task in filtered" :key="task.task_id">
        <div class="task-head">
          <span class="task-no">{{ task.task_no }}</span>
          <span class="task-status" :class="`task-status--${tone(task.status)}`">{{ task.status }}</span>
        </div>
        <div class="h5-row"><span class="k">关联订单</span><span class="v h5-num">{{ task.order_no }}</span></div>
        <div class="h5-row"><span class="k">货物</span><span class="v">{{ task.cargo_name }} · {{ task.quantity || task.weight }}</span></div>
        <div class="h5-row"><span class="k">起运地</span><span class="v">{{ task.shipping.name }}</span></div>
        <div class="h5-row"><span class="k">送达地</span><span class="v">{{ task.receiving.name }}</span></div>
        <div v-if="expanded === task.task_id" class="task-detail">
          <div class="h5-row"><span class="k">计划装货</span><span class="v h5-num">{{ stamp(task.planned_load_at) }}</span></div>
          <div class="h5-row"><span class="k">计划送达</span><span class="v h5-num">{{ stamp(task.planned_deliver_at) }}</span></div>
          <div class="h5-row"><span class="k">车辆</span><span class="v">{{ task.vehicle_plate }} · {{ task.vehicle_type_actual }}</span></div>
        </div>
        <div class="task-actions">
          <van-button size="small" @click="toggle(task.task_id)">{{ expanded === task.task_id ? '收起' : '查看详情' }}</van-button>
          <van-button v-if="task.status === '待司机确认'" size="small" type="danger" @click="openReject(task)">拒绝</van-button>
          <van-button v-if="task.status === '待司机确认'" size="small" type="primary" :loading="busy" @click="onAccept(task)">接单</van-button>
          <van-button v-else-if="['待装货', '运输中'].includes(task.status)" size="small" type="primary" @click="router.push(`/tasks/${task.task_id}/departure`)">查看执行节点</van-button>
          <van-button v-else-if="task.status === '待签收'" size="small" type="primary" @click="router.push(`/tasks/${task.task_id}/signoff`)">去签收</van-button>
        </div>
      </H5Card>
    </main>

    <H5BottomBar>
      <van-button block @click="router.push('/home')">返回工作台</van-button>
    </H5BottomBar>

    <van-popup v-model:show="rejectOpen" position="bottom" round>
      <div class="reject-sheet">
        <h3>拒绝任务</h3>
        <label class="h5-label"><span class="h5-req">*</span>拒绝原因</label>
        <van-field v-model="rejectReason" type="textarea" rows="3" placeholder="请说明拒绝原因" />
        <p v-if="rejectError" class="h5-error">{{ rejectError }}</p>
        <div class="reject-actions">
          <van-button block @click="rejectOpen = false">取消</van-button>
          <van-button block type="danger" :loading="busy" @click="onReject">确认拒绝</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.task-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); margin-bottom: var(--space-2); }
.task-no { font-weight: 600; font-variant-numeric: tabular-nums; color: var(--color-accent); }
.task-status { padding: 2px 8px; border-radius: var(--radius-pill); font-size: var(--font-size-xs); background: var(--color-warning-soft); color: var(--color-warning); }
.task-status--brand { background: var(--color-accent-soft); color: var(--color-accent); }
.task-status--error { background: var(--color-error-soft); color: var(--color-error); }
.task-detail { margin-top: var(--space-2); padding-top: var(--space-2); border-top: 1px dashed var(--color-border); }
.task-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-3); }
.reject-sheet { padding: var(--space-4); }
.reject-sheet h3 { margin: 0 0 var(--space-2); font-size: var(--font-size-md); }
.reject-actions { display: flex; gap: var(--space-2); margin-top: var(--space-4); }
</style>
