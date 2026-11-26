<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { fetchDriverWorkspace } from '@/api/driver'
import { listDriverTasks } from '@/api/dispatch'
import { listMyExpenses } from '@/api/expense'
import H5PageHeader from '@/components/H5PageHeader.vue'
import H5Card from '@/components/H5Card.vue'
import H5StatGrid from '@/components/H5StatGrid.vue'
import H5EmptyState from '@/components/H5EmptyState.vue'
import H5BottomBar from '@/components/H5BottomBar.vue'
import type { DriverSelf } from '@/types/driver'
import type { DriverTask } from '@/types/dispatch'
import type { Expense } from '@/types/expense'

const router = useRouter()
const profile = ref<DriverSelf | null>(null)
const tasks = ref<DriverTask[]>([])
const expenses = ref<Expense[]>([])
const loading = ref(false)

const today = new Date().toISOString().slice(0, 10)
const stats = computed(() => [
  { value: tasks.value.filter((t) => t.planned_load_at.slice(0, 10) === today).length, label: '今日任务' },
  { value: tasks.value.filter((t) => t.status === '待司机确认').length, label: '待确认' },
  { value: tasks.value.filter((t) => t.status === '待装货').length, label: '待装货' },
  { value: tasks.value.filter((t) => t.status === '运输中').length, label: '运输中' },
  { value: tasks.value.filter((t) => t.status === '待签收').length, label: '待签收' },
  { value: expenses.value.filter((e) => e.review_status === '待审核').length, label: '待报销' },
])

const recentTask = computed(() => tasks.value.find((t) => t.status === '运输中') ?? tasks.value[0] ?? null)

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

onMounted(async () => {
  loading.value = true
  try {
    const [self, taskRows, expenseRows] = await Promise.all([
      fetchDriverWorkspace(), listDriverTasks(), listMyExpenses(),
    ])
    profile.value = self
    tasks.value = taskRows
    expenses.value = expenseRows
  } catch (error) {
    showToast(error instanceof Error ? error.message : '加载工作台失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="h5-page h5-page--with-bar">
    <H5PageHeader title="工作台" :show-back="false" />
    <main class="h5-scroll">
      <div class="driver-head">
        <strong>{{ profile?.name || '司机' }}</strong>
        <span>{{ profile?.company_name || '—' }} · {{ profile?.availability || '—' }}</span>
      </div>

      <H5StatGrid :items="stats" />

      <h2 class="h5-section-title">最近任务</h2>
      <H5Card v-if="recentTask">
        <div class="h5-row"><span class="v task-no">{{ recentTask.task_no }}</span></div>
        <div class="h5-row"><span class="k">货物</span><span class="v">{{ recentTask.cargo_name }} · {{ recentTask.weight }}</span></div>
        <div class="h5-row"><span class="k">任务状态</span><span class="v">{{ recentTask.status }}</span></div>
        <div class="h5-row"><span class="k">计划送达</span><span class="v h5-num">{{ stamp(recentTask.planned_deliver_at) }}</span></div>
      </H5Card>
      <H5EmptyState v-else text="暂无最近任务" />

      <h2 class="h5-section-title">公司通知</h2>
      <H5Card><H5EmptyState text="暂无公司通知" /></H5Card>
    </main>

    <H5BottomBar>
      <van-button block type="primary" @click="router.push('/tasks')">查看任务</van-button>
    </H5BottomBar>
  </div>
</template>

<style scoped>
.driver-head { display: flex; flex-direction: column; gap: var(--space-1); margin-bottom: var(--space-4); }
.driver-head strong { font-size: var(--font-size-lg); }
.driver-head span { font-size: var(--font-size-xs); color: var(--color-text-3); }
.task-no { color: var(--color-accent); font-weight: 500; font-variant-numeric: tabular-nums; }
</style>
