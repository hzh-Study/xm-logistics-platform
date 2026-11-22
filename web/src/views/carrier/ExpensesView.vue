<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ApiError } from '@/api/request'
import { listExpenses, markExpensePaid, reviewExpense } from '@/api/expense'
import type { ExpenseFilters } from '@/api/expense'
import type { Expense, ExpenseReviewStatus, ExpenseType } from '@/types/expense'

const expenses = ref<Expense[]>([])
const loading = ref(false)
const saving = ref(false)
const filter = reactive<ExpenseFilters>({})
const types: ExpenseType[] = ['油费', '过路费', '停车费', '维修费', '其他']
const reviewStatuses: ExpenseReviewStatus[] = ['待审核', '审核通过', '审核驳回']
const reviewVisible = ref(false)
const reviewTarget = ref<Expense | null>(null)
const reviewDecision = ref<ExpenseReviewStatus>('审核通过')
const reviewReason = ref('')

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    expenses.value = await listExpenses({
      ...filter,
      submitted_from: toIso(filter.submitted_from ?? ''),
      submitted_to: toIso(filter.submitted_to ?? ''),
    })
  } catch (error) {
    report(error, '读取费用列表失败')
  } finally {
    loading.value = false
  }
}

function report(error: unknown, fallback: string): void {
  if (error instanceof ApiError && Array.isArray(error.details)) {
    const first = error.details[0] as { field?: string; message?: string }
    ElMessage.error(`${first.field ?? '字段'}：${first.message ?? fallback}`)
    return
  }
  ElMessage.error(error instanceof Error ? error.message : fallback)
}

function toIso(value: string): string {
  if (!value) return ''
  return value.length === 16 ? `${value}:00+00:00` : value
}

function resetFilter(): void {
  Object.assign(filter, {
    driver_account_id: undefined,
    task_id: undefined,
    expense_type: undefined,
    submitted_from: undefined,
    submitted_to: undefined,
    review_status: undefined,
    payment_status: undefined,
  })
  void load()
}

function openReview(row: Expense, decision: ExpenseReviewStatus): void {
  reviewTarget.value = row
  reviewDecision.value = decision
  reviewReason.value = ''
  reviewVisible.value = true
}

async function submitReview(): Promise<void> {
  if (!reviewTarget.value) return
  if (reviewDecision.value === '审核驳回' && !reviewReason.value.trim()) {
    ElMessage.error('驳回原因必填，司机将看到该原因')
    return
  }
  saving.value = true
  try {
    await reviewExpense(reviewTarget.value.id, reviewDecision.value, reviewReason.value.trim())
    ElMessage.success(reviewDecision.value === '审核通过' ? '费用已审核通过' : '已驳回并通知司机')
    reviewVisible.value = false
    await load()
  } catch (error) {
    report(error, '审核失败')
  } finally {
    saving.value = false
  }
}

async function onPaid(row: Expense): Promise<void> {
  try {
    await ElMessageBox.confirm('确认已线下付款并标记该笔费用为已支付？', '标记已支付')
  } catch {
    return
  }
  saving.value = true
  try {
    await markExpensePaid(row.id)
    ElMessage.success('已标记已支付')
    await load()
  } catch (error) {
    report(error, '标记已支付失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="expenses">
    <h1>费用审核</h1>
    <p class="intro">按司机、运输任务、费用类型、提交时间与审核状态筛选；审核与支付分别处理。</p>

    <div class="filters">
      <label>司机账号 ID <input v-model.number="filter.driver_account_id" type="number" min="1" /></label>
      <label>任务 ID <input v-model.number="filter.task_id" type="number" min="1" /></label>
      <label>
        费用类型
        <select v-model="filter.expense_type">
          <option value="">全部</option>
          <option v-for="type in types" :key="type" :value="type">{{ type }}</option>
        </select>
      </label>
      <label>提交起 <input v-model="filter.submitted_from" type="datetime-local" /></label>
      <label>提交止 <input v-model="filter.submitted_to" type="datetime-local" /></label>
      <label>
        审核状态
        <select v-model="filter.review_status">
          <option value="">全部</option>
          <option v-for="status in reviewStatuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <div class="filter-actions">
        <button class="btn primary" type="button" @click="load">筛选</button>
        <button class="btn ghost" type="button" @click="resetFilter">重置</button>
      </div>
    </div>

    <el-table :data="expenses" v-loading="loading" border style="width: 100%">
      <el-table-column prop="expense_no" label="费用编号" min-width="150" />
      <el-table-column label="司机 / 任务" min-width="160">
        <template #default="{ row }">
          <div>{{ (row as Expense).driver_name }}（{{ (row as Expense).driver_account_id }}）</div>
          <div class="muted">{{ (row as Expense).task_no }}</div>
        </template>
      </el-table-column>
      <el-table-column label="类型 / 金额" min-width="120">
        <template #default="{ row }">
          {{ (row as Expense).expense_type }} · {{ (row as Expense).amount_yuan }} 元
        </template>
      </el-table-column>
      <el-table-column prop="incurred_at" label="发生时间" min-width="170" />
      <el-table-column label="审核 / 支付" min-width="120">
        <template #default="{ row }">
          <div>{{ (row as Expense).review_status }}</div>
          <div class="muted">{{ (row as Expense).payment_status }}</div>
        </template>
      </el-table-column>
      <el-table-column label="说明 / 驳回原因" min-width="180">
        <template #default="{ row }">
          <div>{{ (row as Expense).description }}</div>
          <div v-if="(row as Expense).review_reason" class="reason">
            驳回原因：{{ (row as Expense).review_reason }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="凭证" min-width="170">
        <template #default="{ row }">
          <div v-for="path in (row as Expense).vouchers" :key="path" class="muted">{{ path }}</div>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="200" fixed="right">
        <template #default="{ row }">
          <template v-if="(row as Expense).review_status === '待审核'">
            <button class="btn small" type="button" :disabled="saving" @click="openReview(row as Expense, '审核通过')">通过</button>
            <button class="btn small ghost" type="button" :disabled="saving" @click="openReview(row as Expense, '审核驳回')">驳回</button>
          </template>
          <button
            v-else-if="(row as Expense).review_status === '审核通过' && (row as Expense).payment_status === '待支付'"
            class="btn small"
            type="button"
            :disabled="saving"
            @click="onPaid(row as Expense)"
          >
            标记已支付
          </button>
          <span v-else class="muted">已处理</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="reviewVisible" :title="reviewDecision === '审核通过' ? '审核通过' : '审核驳回'" width="460px">
      <template v-if="reviewTarget">
        <p class="dialog-line">{{ reviewTarget.expense_no }} · {{ reviewTarget.expense_type }} {{ reviewTarget.amount_yuan }} 元</p>
        <label class="dialog-field">
          <span>驳回原因（驳回必填，司机可见）</span>
          <textarea v-model="reviewReason" rows="3" maxlength="500" placeholder="请说明驳回原因" />
        </label>
      </template>
      <template #footer>
        <button class="btn ghost" type="button" @click="reviewVisible = false">取消</button>
        <button class="btn primary" type="button" :disabled="saving" @click="submitReview">确认</button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.expenses h1 { margin: 0 0 var(--space-2); font-size: var(--font-size-xl); }
.intro { margin: 0 0 var(--space-4); color: var(--color-text-muted); font-size: var(--font-size-sm); }
.filters { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: flex-end; margin-bottom: var(--space-4); padding: var(--space-4); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius); }
.filters label { display: flex; flex-direction: column; gap: var(--space-1); font-size: var(--font-size-sm); color: var(--color-text-muted); }
.filters input, .filters select { min-height: 36px; padding: 0 var(--space-2); font: inherit; color: var(--color-text); background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius); }
.filter-actions { display: flex; gap: var(--space-2); }
.btn { min-height: 36px; padding: 0 var(--space-3); font: inherit; border-radius: var(--radius); cursor: pointer; }
.btn.primary { color: #fff; background: var(--color-accent); border: 1px solid var(--color-accent); }
.btn.ghost { color: var(--color-text); background: var(--color-surface); border: 1px solid var(--color-border); }
.btn.small { min-height: 30px; padding: 0 var(--space-2); font-size: var(--font-size-sm); }
.btn:disabled { opacity: 0.6; cursor: default; }
.muted { color: var(--color-text-muted); font-size: var(--font-size-sm); }
.reason { color: var(--color-error); font-size: var(--font-size-sm); }
.dialog-line { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.dialog-field { display: flex; flex-direction: column; gap: var(--space-2); font-size: var(--font-size-sm); }
.dialog-field textarea { padding: var(--space-2); font: inherit; color: var(--color-text); background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius); }
</style>
