<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import { listExpenses, markExpensePaid, reviewExpense } from '@/api/expense'
import type { ExpenseFilters } from '@/api/expense'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import StatusPill from '@/components/StatusPill.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import PhotoGrid from '@/components/PhotoGrid.vue'
import type { Expense, ExpenseReviewStatus, ExpenseType } from '@/types/expense'

const expenses = ref<Expense[]>([])
const loading = ref(false)
const saving = ref(false)
const filter = reactive<ExpenseFilters>({})
const types: ExpenseType[] = ['油费', '过路费', '停车费', '维修费', '其他']

const reviewOpen = ref(false)
const reviewTarget = ref<Expense | null>(null)
const reviewDecision = ref<ExpenseReviewStatus>('审核通过')
const reviewReason = ref('')
const reviewError = ref('')
const detailOpen = ref(false)
const detailTarget = ref<Expense | null>(null)
const payTarget = ref<Expense | null>(null)
const payOpen = ref(false)

function displayReview(status: string): string {
  return status === '审核驳回' ? '审核不通过' : status
}

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

const filtered = () => expenses.value.filter((expense) =>
  (!filter.expense_type || expense.expense_type === filter.expense_type) &&
  (!filter.review_status || expense.review_status === filter.review_status) &&
  (!filter.payment_status || expense.payment_status === filter.payment_status) &&
  (!filter.task_id || expense.task_no.includes(String(filter.task_id))),
)

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
    driver_account_id: undefined, task_id: undefined, expense_type: undefined,
    submitted_from: undefined, submitted_to: undefined, review_status: undefined, payment_status: undefined,
  })
  void load()
}

function openReview(row: Expense, decision: ExpenseReviewStatus): void {
  reviewTarget.value = row
  reviewDecision.value = decision
  reviewReason.value = ''
  reviewError.value = ''
  reviewOpen.value = true
}

async function submitReview(): Promise<void> {
  if (!reviewTarget.value) return
  if (reviewDecision.value === '审核驳回' && !reviewReason.value.trim()) {
    reviewError.value = '驳回原因为必填项，司机将看到该原因。'
    return
  }
  saving.value = true
  try {
    await reviewExpense(reviewTarget.value.id, reviewDecision.value, reviewReason.value.trim())
    ElMessage.success(reviewDecision.value === '审核通过' ? '费用已审核通过' : '已驳回并通知司机')
    reviewOpen.value = false
    await load()
  } catch (error) {
    report(error, '审核失败')
  } finally {
    saving.value = false
  }
}

function openDetail(row: Expense): void {
  detailTarget.value = row
  detailOpen.value = true
}

function askPaid(row: Expense): void {
  payTarget.value = row
  payOpen.value = true
}

async function markPaid(): Promise<void> {
  const target = payTarget.value
  if (!target) return
  saving.value = true
  try {
    await markExpensePaid(target.id)
    ElMessage.success('已标记已支付')
    payOpen.value = false
    detailOpen.value = false
    await load()
  } catch (error) {
    report(error, '标记已支付失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="费用审核" :subtitle="`待审核 ${expenses.filter((item) => item.review_status === '待审核').length} · 审核通过 ${expenses.filter((item) => item.review_status === '审核通过').length} · 审核不通过 ${expenses.filter((item) => item.review_status === '审核驳回').length}`">
      <template #actions><el-button @click="load">刷新</el-button></template>
    </PageHeader>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="ex-task">任务编号</label><el-input id="ex-task" v-model="filter.task_id" placeholder="请输入任务编号" clearable /></div>
        <div class="field">
          <label class="field__label" for="ex-type">费用类型</label>
          <el-select id="ex-type" v-model="filter.expense_type" placeholder="全部" clearable>
            <el-option v-for="item in types" :key="item" :label="item === '维修费' ? '维修' : item" :value="item" />
          </el-select>
        </div>
        <div class="field"><label class="field__label">提交时间</label><el-date-picker v-model="filter.submitted_from" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" class="date-input" /></div>
        <div class="field"><label class="field__label">提交时间（止）</label><el-date-picker v-model="filter.submitted_to" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" class="date-input" /></div>
        <div class="field">
          <label class="field__label" for="ex-review">审核状态</label>
          <el-select id="ex-review" v-model="filter.review_status" placeholder="全部" clearable>
            <el-option label="待审核" value="待审核" />
            <el-option label="审核通过" value="审核通过" />
            <el-option label="审核不通过" value="审核驳回" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="ex-pay">支付状态</label>
          <el-select id="ex-pay" v-model="filter.payment_status" placeholder="全部" clearable>
            <el-option label="待支付" value="待支付" /><el-option label="已支付" value="已支付" />
          </el-select>
        </div>
      </div>
      <div class="filter-actions">
        <el-button @click="resetFilter">重置</el-button>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">报销费用列表</span><span class="panel-hint">报销费用由司机按运输任务提交 · 单条处理，非批量</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!filtered().length" text="暂无报销费用" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">费用编号</th><th>司机 / 任务</th><th>费用类型</th><th class="num">金额</th><th class="num">提交时间</th><th>审核状态</th><th>支付状态</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in filtered()" :key="row.id">
                <td class="num">{{ row.expense_no }}</td>
                <td>{{ row.driver_name }}<div class="cell-sub">{{ row.task_no }}</div></td>
                <td>{{ row.expense_type === '维修费' ? '维修' : row.expense_type }}</td>
                <td class="num">¥ {{ row.amount_yuan }}</td>
                <td class="num">{{ stamp(row.incurred_at) }}</td>
                <td><StatusPill :text="displayReview(row.review_status)" /></td>
                <td><StatusPill :text="row.payment_status" /></td>
                <td class="ops">
                  <el-button v-if="row.review_status === '待审核'" type="primary" link @click="openReview(row, '审核通过')">审核</el-button>
                  <el-button v-if="row.review_status === '审核通过' && row.payment_status === '待支付'" type="primary" link @click="askPaid(row)">标记已支付</el-button>
                  <el-button v-if="row.review_status === '审核驳回'" type="primary" link @click="openDetail(row)">查看原因</el-button>
                  <el-button type="primary" link @click="openDetail(row)">查看详情</el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ filtered().length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="reviewOpen" :title="`费用审核 · ${reviewTarget?.expense_no ?? ''}`">
      <template #body>
        <template v-if="reviewTarget">
          <NoticeBar tone="info">审核状态与支付状态相互独立：审核通过不代表已支付；线下支付后由本公司单条标记「已支付」并记录操作人与时间。</NoticeBar>
          <dl class="kv section-gap">
            <dt>费用编号</dt><dd class="num">{{ reviewTarget.expense_no }}</dd>
            <dt>司机</dt><dd>{{ reviewTarget.driver_name }}</dd>
            <dt>关联任务</dt><dd class="num">{{ reviewTarget.task_no }}</dd>
            <dt>费用类型</dt><dd>{{ reviewTarget.expense_type }}</dd>
            <dt>金额</dt><dd class="num">¥ {{ reviewTarget.amount_yuan }}</dd>
            <dt>提交时间</dt><dd class="num">{{ stamp(reviewTarget.incurred_at) }}</dd>
            <dt>费用说明</dt><dd>{{ reviewTarget.description }}</dd>
          </dl>
          <PhotoGrid v-if="reviewTarget.vouchers.length" :photos="reviewTarget.vouchers" />
          <div class="field section-gap">
            <label class="field__label" for="ex-reason"><span v-if="reviewDecision === '审核驳回'" class="field__req">*</span>驳回原因（驳回时必填）</label>
            <el-input id="ex-reason" v-model="reviewReason" type="textarea" :rows="3" placeholder="请填写驳回原因，司机可见" />
            <p v-if="reviewError" class="field__error">{{ reviewError }}</p>
          </div>
        </template>
      </template>
      <template #footer>
        <el-button @click="reviewOpen = false">关闭</el-button>
        <el-button type="danger" @click="reviewTarget && openReview(reviewTarget, '审核驳回')">驳回</el-button>
        <el-button type="primary" :loading="saving" @click="submitReview">审核通过</el-button>
      </template>
    </DetailDrawer>

    <DetailDrawer v-model="detailOpen" :title="`费用详情 · ${detailTarget?.expense_no ?? ''}`">
      <template #body>
        <template v-if="detailTarget">
          <NoticeBar v-if="detailTarget.review_reason" tone="error">驳回原因：{{ detailTarget.review_reason }}</NoticeBar>
          <dl class="kv section-gap">
            <dt>费用编号</dt><dd class="num">{{ detailTarget.expense_no }}</dd>
            <dt>金额</dt><dd class="num">¥ {{ detailTarget.amount_yuan }}</dd>
            <dt>审核状态</dt><dd><StatusPill :text="displayReview(detailTarget.review_status)" /></dd>
            <dt>支付状态</dt><dd><StatusPill :text="detailTarget.payment_status" /></dd>
            <dt>关联任务</dt><dd class="num">{{ detailTarget.task_no }}</dd>
          </dl>
          <PhotoGrid v-if="detailTarget.vouchers.length" :photos="detailTarget.vouchers" />
        </template>
      </template>
      <template #footer>
        <el-button @click="detailOpen = false">关闭</el-button>
        <el-button v-if="detailTarget?.review_status === '审核通过' && detailTarget.payment_status === '待支付'" type="primary" @click="askPaid(detailTarget)">标记已支付</el-button>
      </template>
    </DetailDrawer>

    <ConfirmDialog v-model="payOpen" title="标记已支付" confirm-text="确认已支付" @confirm="markPaid">
      确认已在线下完成支付？提交后将记录操作人与操作时间，支付状态变为「已支付」。
    </ConfirmDialog>
  </section>
</template>

<style scoped>
.date-input { width: 100%; }
.section-gap { margin-top: var(--space-4); }
</style>
