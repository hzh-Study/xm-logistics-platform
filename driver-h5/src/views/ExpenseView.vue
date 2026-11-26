<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getDriverTask, listDriverTasks } from '@/api/dispatch'
import { listMyExpenses, resubmitExpense, submitExpense } from '@/api/expense'
import type { ExpensePayload } from '@/api/expense'
import H5PageHeader from '@/components/H5PageHeader.vue'
import H5Card from '@/components/H5Card.vue'
import H5Notice from '@/components/H5Notice.vue'
import H5Uploader from '@/components/H5Uploader.vue'
import H5BottomBar from '@/components/H5BottomBar.vue'
import type { DriverTask } from '@/types/dispatch'
import type { Expense, ExpenseType } from '@/types/expense'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.params.taskId)
const task = ref<DriverTask | null>(null)
const tasks = ref<DriverTask[]>([])
const expenses = ref<Expense[]>([])
const busy = ref(false)
const resubmitTarget = ref<number | null>(null)

const types: { label: string; value: ExpenseType }[] = [
  { label: '油费', value: '油费' },
  { label: '过路费', value: '过路费' },
  { label: '停车费', value: '停车费' },
  { label: '维修', value: '维修费' },
  { label: '其它', value: '其他' },
]

const blank = (): ExpensePayload => ({
  expense_type: '油费', amount_yuan: '', incurred_at: '', description: '', vouchers: [],
})
const form = ref<ExpensePayload>(blank())
const selectedTaskNo = ref('')

const taskExpenses = computed(() => expenses.value.filter((item) => item.task_id === taskId))

function displayReview(status: string): string {
  return status === '审核驳回' ? '审核不通过' : status
}

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function toIso(value: string): string {
  if (!value) return ''
  return value.length === 16 ? `${value}:00+00:00` : value
}

function onFileChange(files: File[]): void {
  form.value.vouchers = files.map((file) => `uploads/${file.name}`)
}

async function load(): Promise<void> {
  busy.value = true
  try {
    const [detail, taskRows, mine] = await Promise.all([
      getDriverTask(taskId), listDriverTasks(), listMyExpenses(),
    ])
    task.value = detail
    selectedTaskNo.value = detail.task_no
    tasks.value = taskRows
    expenses.value = mine
  } catch (error) {
    showToast(error instanceof Error ? error.message : '读取费用失败')
  } finally {
    busy.value = false
  }
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

onMounted(load)
</script>

<template>
  <div class="h5-page h5-page--with-bar">
    <H5PageHeader title="费用提交" />
    <main class="h5-scroll">
      <H5Notice tone="info">单次提交一笔报销费用，凭证与关联任务需填写完整。报销进度可在费用记录中查看。</H5Notice>

      <H5Card>
        <label class="h5-label"><span class="h5-req">*</span>费用类型</label>
        <van-radio-group v-model="form.expense_type" class="ex-kinds">
          <van-radio v-for="item in types" :key="item.value" :name="item.value">{{ item.label }}</van-radio>
        </van-radio-group>

        <label class="h5-label"><span class="h5-req">*</span>金额（元）</label>
        <van-field v-model="form.amount_yuan" type="number" placeholder="请输入金额" />

        <label class="h5-label"><span class="h5-req">*</span>关联运输任务</label>
        <van-field name="task" label="任务">
          <template #input>
            <van-radio-group v-model="selectedTaskNo" direction="vertical">
              <van-radio v-for="item in tasks.slice(0, 6)" :key="item.task_id" :name="item.task_no">
                {{ item.task_no }} · {{ item.cargo_name }}
              </van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <p class="h5-help">当前任务：{{ task?.task_no || '—' }} · {{ task?.cargo_name || '—' }}</p>

        <H5Uploader label="费用凭证（支持多张）" multiple :status="form.vouchers.length ? 'done' : 'idle'" @change="onFileChange" />
        <p v-if="form.vouchers.length" class="h5-help">已选择 {{ form.vouchers.length }} 张凭证（本地选择，凭证路径写入提交）</p>

        <label class="h5-label">发生时间</label>
        <van-field v-model="form.incurred_at" placeholder="YYYY-MM-DDTHH:mm" />
        <label class="h5-label">费用说明</label>
        <van-field v-model="form.description" type="textarea" rows="2" placeholder="请说明费用用途" />
      </H5Card>

      <h2 class="h5-section-title">费用记录</h2>
      <H5Card v-for="item in taskExpenses" :key="item.id">
        <div class="h5-row"><span class="v">{{ item.expense_type }} · ¥ {{ item.amount_yuan }}</span><span class="v">{{ displayReview(item.review_status) }}</span></div>
        <div class="h5-row"><span class="k">费用编号</span><span class="v h5-num">{{ item.expense_no }}</span></div>
        <p v-if="item.review_reason" class="reject-reason">驳回原因：{{ item.review_reason }}</p>
        <div v-if="item.review_status === '审核驳回'" class="task-actions">
          <van-button size="small" type="primary" @click="openResubmit(item)">重新提交</van-button>
        </div>
      </H5Card>
    </main>

    <H5BottomBar>
      <van-button block @click="router.push('/expenses')">费用记录</van-button>
      <van-button block type="primary" :loading="busy" @click="onSubmit">提交</van-button>
    </H5BottomBar>
  </div>
</template>

<style scoped>
.ex-kinds { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-2); padding: var(--space-2) 0; }
.task-actions { display: flex; gap: var(--space-2); margin-top: var(--space-3); }
.reject-reason { margin: var(--space-2) 0 0; font-size: var(--font-size-xs); color: var(--color-error); }
</style>
