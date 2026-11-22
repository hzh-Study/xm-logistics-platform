<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getDriverTask } from '@/api/dispatch'
import { listMyExpenses, resubmitExpense, submitExpense } from '@/api/expense'
import type { ExpensePayload } from '@/api/expense'
import type { DriverTask } from '@/types/dispatch'
import type { Expense, ExpenseType } from '@/types/expense'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.params.taskId)
const task = ref<DriverTask | null>(null)
const expenses = ref<Expense[]>([])
const busy = ref(false)
const resubmitTarget = ref<number | null>(null)
const types: ExpenseType[] = ['油费', '过路费', '停车费', '维修费', '其他']

const blank = (): ExpensePayload => ({
  expense_type: '油费',
  amount_yuan: '',
  incurred_at: '',
  description: '',
  vouchers: [''],
})
const form = ref<ExpensePayload>(blank())
const taskExpenses = computed(() => expenses.value.filter((item) => item.task_id === taskId))

onMounted(load)

async function load(): Promise<void> {
  busy.value = true
  try {
    const [detail, mine] = await Promise.all([getDriverTask(taskId), listMyExpenses()])
    task.value = detail
    expenses.value = mine
  } catch (error) {
    showToast(error instanceof Error ? error.message : '读取费用失败')
  } finally {
    busy.value = false
  }
}

function toIso(value: string): string {
  if (!value) return ''
  return value.length === 16 ? `${value}:00+00:00` : value
}

function openResubmit(item: Expense): void {
  resubmitTarget.value = item.id
  form.value = {
    expense_type: item.expense_type,
    amount_yuan: item.amount_yuan,
    incurred_at: item.incurred_at.slice(0, 16),
    description: item.description,
    vouchers: [...item.vouchers],
  }
}

function resetForm(): void {
  resubmitTarget.value = null
  form.value = blank()
}

async function onSubmit(): Promise<void> {
  const payload = form.value
  const vouchers = payload.vouchers.map((path) => path.trim()).filter(Boolean)
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(payload.amount_yuan) || Number(payload.amount_yuan) <= 0) {
    showToast('请填写大于零的金额，最多两位小数')
    return
  }
  if (!payload.incurred_at || !payload.description.trim() || vouchers.length === 0) {
    showToast('请填写发生时间、说明与至少一张凭证')
    return
  }
  busy.value = true
  try {
    const body: ExpensePayload = {
      ...payload,
      incurred_at: toIso(payload.incurred_at),
      description: payload.description.trim(),
      vouchers,
    }
    if (resubmitTarget.value !== null) {
      await resubmitExpense(resubmitTarget.value, body)
      showToast('已重新提交，等待公司审核')
    } else {
      await submitExpense(taskId, body)
      showToast('报销费用已提交，等待公司审核')
    }
    resetForm()
    await load()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '提交失败')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="expense-page">
    <header class="topbar">
      <button class="back" type="button" @click="router.replace('/tasks')">返回</button>
      <span>费用报销</span>
      <span class="state">{{ task?.status ?? '—' }}</span>
    </header>

    <main class="body">
      <section class="card">
        <h2>任务信息</h2>
        <div class="row"><span>任务号</span><span>{{ task?.task_no ?? '—' }}</span></div>
        <div class="row"><span>任务状态</span><span>{{ task?.status ?? '—' }}</span></div>
      </section>

      <section class="card">
        <h2>{{ resubmitTarget === null ? '提交费用' : '重新提交（关联原笔）' }}</h2>
        <label class="field">
          <span>费用类型</span>
          <select v-model="form.expense_type">
            <option v-for="type in types" :key="type" :value="type">{{ type }}</option>
          </select>
        </label>
        <label class="field"><span>金额（元）</span><input v-model="form.amount_yuan" inputmode="decimal" placeholder="如 288.50" /></label>
        <label class="field"><span>发生时间</span><input v-model="form.incurred_at" type="datetime-local" /></label>
        <label class="field"><span>费用说明</span><input v-model="form.description" placeholder="如 高速服务区加油" /></label>
        <div class="vouchers">
          <span class="label">费用凭证（相对路径）</span>
          <div v-for="(_, index) in form.vouchers" :key="index" class="voucher-row">
            <input v-model="form.vouchers[index]" placeholder="vouchers/expense/ticket.jpg" />
            <button class="btn small" type="button" @click="form.vouchers.splice(index, 1)">移除</button>
          </div>
          <button class="btn ghost" type="button" @click="form.vouchers.push('')">添加凭证</button>
        </div>
        <div class="actions">
          <button class="btn primary" type="button" :disabled="busy" @click="onSubmit">
            {{ resubmitTarget === null ? '提交费用' : '确认重提' }}
          </button>
          <button v-if="resubmitTarget !== null" class="btn ghost" type="button" @click="resetForm">取消重提</button>
        </div>
      </section>

      <section class="card">
        <h2>本任务费用记录</h2>
        <p v-if="taskExpenses.length === 0" class="empty">本任务暂无费用记录</p>
        <article v-for="item in taskExpenses" :key="item.id" class="record">
          <div class="row"><span>{{ item.expense_no }}</span><span>{{ item.expense_type }} {{ item.amount_yuan }} 元</span></div>
          <div class="row"><span>审核</span><span>{{ item.review_status }}</span></div>
          <div class="row"><span>支付</span><span>{{ item.payment_status }}</span></div>
          <p v-if="item.review_reason" class="reason">驳回原因：{{ item.review_reason }}</p>
          <p class="hint">凭证 {{ item.vouchers.length }} 张 · {{ item.description }}</p>
          <p v-if="item.superseded_by" class="hint">已重提为新笔 {{ item.superseded_by }}</p>
          <button
            v-if="item.review_status === '审核驳回' && !item.superseded_by"
            class="btn ghost"
            type="button"
            @click="openResubmit(item)"
          >
            重新提交
          </button>
        </article>
      </section>
    </main>
  </div>
</template>

<style scoped>
.expense-page { display: flex; flex-direction: column; min-height: 100vh; }
.topbar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); padding: var(--space-4); background: var(--color-surface); border-bottom: 1px solid var(--color-border); font-size: var(--font-size-md); }
.back { min-height: var(--tap-min); padding: 0 var(--space-2); font: inherit; color: var(--color-text); background: transparent; border: 0; }
.state { font-size: var(--font-size-sm); color: var(--color-accent); }
.body { flex: 1; padding: var(--space-4); }
.card { margin-bottom: var(--space-3); padding: var(--space-4); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius); }
.card h2 { margin: 0 0 var(--space-3); font-size: var(--font-size-md); }
.row { display: flex; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-2); font-size: var(--font-size-sm); }
.row > span:first-child { flex-shrink: 0; color: var(--color-text-muted); }
.field { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); font-size: var(--font-size-sm); }
.field > span { flex-shrink: 0; width: 7em; color: var(--color-text-muted); }
.field input, .field select, .voucher-row input { flex: 1; min-width: 0; min-height: var(--tap-min); padding: 0 var(--space-2); font: inherit; color: var(--color-text); background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius); }
.vouchers { margin-top: var(--space-2); }
.label { display: block; margin-bottom: var(--space-2); font-size: var(--font-size-sm); color: var(--color-text-muted); }
.voucher-row { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.actions { display: flex; gap: var(--space-2); margin-top: var(--space-3); }
.btn { min-height: var(--tap-min); padding: 0 var(--space-4); font: inherit; border-radius: var(--radius); cursor: pointer; }
.btn.primary { color: #fff; background: var(--color-accent); border: 1px solid var(--color-accent); }
.btn.ghost { color: var(--color-text); background: var(--color-surface); border: 1px solid var(--color-border); }
.btn.small { padding: 0 var(--space-3); }
.btn:disabled { opacity: 0.6; cursor: default; }
.record { padding: var(--space-3) 0; border-top: 1px solid var(--color-border); }
.empty { color: var(--color-text-muted); font-size: var(--font-size-sm); }
.reason { margin: var(--space-1) 0; font-size: var(--font-size-sm); color: var(--color-error); }
.hint { margin: var(--space-1) 0; font-size: var(--font-size-sm); color: var(--color-text-muted); }
</style>
