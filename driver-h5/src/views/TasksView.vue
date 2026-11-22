<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { acceptTask, listDriverTasks, rejectTask } from '@/api/dispatch'
import type { DriverTask } from '@/types/dispatch'

const router = useRouter()
const tasks = ref<DriverTask[]>([])
const loading = ref(false)
const expanded = ref<number | null>(null)
const rejectTarget = ref<DriverTask | null>(null)
const rejectReason = ref('')
const busy = ref(false)

onMounted(load)

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

function toggle(taskId: number): void {
  expanded.value = expanded.value === taskId ? null : taskId
}

async function onAccept(task: DriverTask): Promise<void> {
  busy.value = true
  try {
    const updated = await acceptTask(task.task_id)
    showToast('已确认，任务进入待装货')
    await replace(updated)
    await load()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '确认失败')
  } finally {
    busy.value = false
  }
}

function openReject(task: DriverTask): void {
  rejectTarget.value = task
  rejectReason.value = ''
}

async function onReject(): Promise<void> {
  const task = rejectTarget.value
  if (!task) return
  if (!rejectReason.value.trim()) {
    showToast('请填写拒绝原因')
    return
  }
  busy.value = true
  try {
    const updated = await rejectTask(task.task_id, rejectReason.value)
    showToast('已拒绝该任务')
    await replace(updated)
    rejectTarget.value = null
    await load()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '拒绝失败')
  } finally {
    busy.value = false
  }
}

function replace(updated: DriverTask): void {
  tasks.value = tasks.value.map((row) =>
    row.task_id === updated.task_id ? updated : row,
  )
}
</script>

<template>
  <div class="tasks-page">
    <header class="topbar">
      <button class="back" type="button" @click="router.replace('/home')">返回</button>
      <span>我的运输任务</span>
      <span class="count">{{ tasks.length }} 条</span>
    </header>
    <main class="body">
      <p v-if="loading" class="empty">加载中…</p>
      <p v-else-if="tasks.length === 0" class="empty">暂无运输任务</p>
      <article v-for="task in tasks" :key="task.task_id" class="task-card">
        <button class="card-head" type="button" @click="toggle(task.task_id)">
          <span class="task-no">{{ task.task_no }}</span>
          <span class="status" :class="{ pending: task.status === '待司机确认' }">{{ task.status }}</span>
          <span class="chevron">{{ expanded === task.task_id ? '收起' : '详情' }}</span>
        </button>
        <div class="summary">
          <span>{{ task.cargo_name }} · {{ task.weight || task.quantity || '货物' }}</span>
          <span>{{ task.vehicle_plate }}</span>
        </div>
        <div class="window">计划装货 {{ task.planned_load_at }} → 送达 {{ task.planned_deliver_at }}</div>

        <div v-if="expanded === task.task_id" class="detail">
          <div class="row"><span>订单号</span><span>{{ task.order_no }}</span></div>
          <div class="row"><span>承运公司</span><span>{{ task.carrier_company }}</span></div>
          <div class="row"><span>车型 / 车长</span><span>{{ task.vehicle_type }} / {{ task.vehicle_length }}</span></div>
          <div class="row">
            <span>发货</span>
            <span>{{ task.shipping.name }} · {{ task.shipping.contact }} · {{ task.shipping.phone }}</span>
          </div>
          <div class="row"><span>发货地址</span><span>{{ task.shipping.detail_address }}</span></div>
          <div class="row">
            <span>收货</span>
            <span>{{ task.receiving.name }} · {{ task.receiving.contact }} · {{ task.receiving.phone }}</span>
          </div>
          <div class="row"><span>收货地址</span><span>{{ task.receiving.detail_address }}</span></div>
          <div v-if="task.notes" class="row"><span>公司备注</span><span>{{ task.notes }}</span></div>
          <div v-if="task.reject_reason" class="row"><span>拒绝原因</span><span>{{ task.reject_reason }}</span></div>
        </div>

        <div v-if="task.status === '待司机确认'" class="actions">
          <button class="btn primary" type="button" :disabled="busy" @click="onAccept(task)">接受任务</button>
          <button class="btn ghost" type="button" :disabled="busy" @click="openReject(task)">拒绝</button>
        </div>
        <div v-else-if="task.status === '待装货'" class="actions">
          <button
            class="btn primary"
            type="button"
            @click="router.push(`/tasks/${task.task_id}/departure`)"
          >
            发货打卡与起运
          </button>
        </div>
        <div v-else-if="task.status === '运输中' || task.status === '待签收'" class="actions">
          <button
            class="btn primary"
            type="button"
            @click="router.push(`/tasks/${task.task_id}/signoff`)"
          >
            收货打卡与签收
          </button>
        </div>
        <div v-else-if="task.status === '待确认完成'" class="actions">
          <p class="wait-note">签收资料已提交，等待物流公司确认完成</p>
        </div>
        <div v-else-if="task.status === '已完成'" class="actions">
          <button class="btn primary" type="button" @click="router.push(`/tasks/${task.task_id}/expense`)">
            提交报销费用
          </button>
        </div>
        <div v-if="['运输中', '待签收', '待确认完成', '异常'].includes(task.status)" class="actions">
          <button
            class="btn ghost"
            type="button"
            @click="router.push(`/tasks/${task.task_id}/exception`)"
          >
            上报在途异常
          </button>
        </div>
      </article>
    </main>

    <div v-if="rejectTarget" class="mask" @click.self="rejectTarget = null">
      <div class="sheet">
        <h2>拒绝任务</h2>
        <p class="sheet-note">任务 {{ rejectTarget.task_no }} 拒绝后将回到公司待派单，请填写原因。</p>
        <textarea v-model="rejectReason" rows="3" maxlength="500" placeholder="请填写拒绝原因" />
        <div class="sheet-actions">
          <button class="btn ghost" type="button" @click="rejectTarget = null">取消</button>
          <button class="btn danger" type="button" :disabled="busy" @click="onReject">确认拒绝</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tasks-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-md);
}

.back {
  min-height: var(--tap-min);
  padding: 0 var(--space-2);
  font: inherit;
  color: var(--color-text);
  background: transparent;
  border: 0;
}

.count {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.body {
  flex: 1;
  padding: var(--space-4);
}

.empty {
  padding: var(--space-8) var(--space-4);
  text-align: center;
  color: var(--color-text-muted);
}

.task-card {
  margin-bottom: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.card-head {
  display: flex;
  width: 100%;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--tap-min);
  padding: 0;
  font: inherit;
  text-align: left;
  color: var(--color-text);
  background: transparent;
  border: 0;
}

.task-no {
  flex: 1;
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.status {
  padding: 2px var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  background: var(--color-bg);
  border-radius: var(--radius);
}

.status.pending {
  color: var(--color-accent);
}

.chevron {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.summary,
.window {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  margin-top: var(--space-2);
  font-size: var(--font-size-sm);
}

.window {
  color: var(--color-text-muted);
}

.detail {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
  font-size: var(--font-size-sm);
}

.row > span:first-child {
  flex-shrink: 0;
  color: var(--color-text-muted);
}

.row > span:last-child {
  text-align: right;
}

.actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.wait-note {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.btn {
  flex: 1;
  min-height: var(--tap-min);
  font: inherit;
  border-radius: var(--radius);
  cursor: pointer;
}

.btn.primary {
  color: #fff;
  background: var(--color-accent);
  border: 1px solid var(--color-accent);
}

.btn.ghost {
  color: var(--color-text);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.btn.danger {
  color: #fff;
  background: var(--color-error);
  border: 1px solid var(--color-error);
}

.btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: flex-end;
  background: rgb(0 0 0 / 40%);
}

.sheet {
  width: 100%;
  padding: var(--space-6) var(--space-4) calc(var(--space-6) + var(--safe-bottom));
  background: var(--color-surface);
  border-radius: var(--radius) var(--radius) 0 0;
}

.sheet h2 {
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-lg);
}

.sheet-note {
  margin: 0 0 var(--space-4);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.sheet textarea {
  width: 100%;
  padding: var(--space-3);
  font: inherit;
  color: var(--color-text);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.sheet-actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
}
</style>
