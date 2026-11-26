<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCarrierProgress } from '@/api/checkin'
import { confirmSignoff } from '@/api/signoff'
import { listExpenses } from '@/api/expense'
import PageHeader from '@/components/PageHeader.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import ProcessStepper from '@/components/ProcessStepper.vue'
import ProcessTimeline from '@/components/ProcessTimeline.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { ProcessStep } from '@/components/ProcessStepper.vue'
import type { TimelineItem } from '@/components/ProcessTimeline.vue'
import type { TaskProgress } from '@/types/checkin'
import type { Expense } from '@/types/expense'

const route = useRoute()
const taskId = Number(route.params.taskId)
const progress = ref<TaskProgress | null>(null)
const expenses = ref<Expense[]>([])
const loading = ref(false)
const confirming = ref(false)
const confirmOpen = ref(false)

const statuses = ['待司机确认', '待装货', '运输中', '待签收', '待确认完成', '已完成']

const steps = computed<ProcessStep[]>(() => {
  const p = progress.value
  if (!p) return []
  const current = statuses.indexOf(p.task_status)
  return statuses.map((label, index) => ({
    label,
    done: current >= 0 && index < current,
    current: index === current,
    time: index === 2 ? stamp(p.checkins[0]?.arrived_at ?? '') : undefined,
  }))
})

const timeline = computed<TimelineItem[]>(() => {
  const p = progress.value
  if (!p) return []
  const items: TimelineItem[] = []
  p.checkins.forEach((item) => items.push({
    title: '发货地打卡',
    meta: `${stamp(item.arrived_at)} · ${item.position_status}${item.distance_m !== null ? ` · 距离快照 ${item.distance_m} 米` : ''}`,
    desc: item.notes || undefined,
    photos: item.photos,
  }))
  p.loading_photos.forEach((item) => items.push({ title: `装货照片 · ${item.phase}`, meta: stamp(item.created_at), photos: item.paths }))
  p.loading_anomalies.forEach((item) => items.push({ title: `装货异常 · ${item.kind}`, meta: stamp(item.created_at), desc: item.detail, photos: item.photos }))
  if (p.confirmation) items.push({ title: '起运确认', meta: stamp(p.confirmation.created_at), desc: '货物与车辆已核对' })
  p.arrival_checkins.forEach((item) => items.push({
    title: '到达收货地打卡',
    meta: `${stamp(item.arrived_at)} · ${item.position_status}${item.distance_m !== null ? ` · 距离快照 ${item.distance_m} 米` : ''}`,
    desc: item.notes || undefined,
    photos: item.photos,
  }))
  if (p.signoff_voucher) items.push({ title: '签收与凭证', meta: stamp(p.signoff_voucher.received_at), desc: `${p.signoff_voucher.receiver_name} · ${p.signoff_voucher.receiving_condition}`, photos: [...p.signoff_voucher.signature_photos, ...p.signoff_voucher.vouchers] })
  return items
})

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function displayReview(status: string): string {
  return status === '审核驳回' ? '审核不通过' : status
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [progressData, expenseRows] = await Promise.all([
      getCarrierProgress(taskId),
      listExpenses({ task_id: taskId }),
    ])
    progress.value = progressData
    expenses.value = expenseRows
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取运输进度失败')
  } finally {
    loading.value = false
  }
}

async function confirm(): Promise<void> {
  if (!progress.value?.signoff_voucher) {
    ElMessage.warning('司机尚未提交签收凭证')
    return
  }
  confirming.value = true
  try {
    progress.value = await confirmSignoff(taskId, { confirmed: true, notes: '凭证齐全，确认完成' })
    ElMessage.success('已确认完成，运输任务与运输订单均已完成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '确认失败')
  } finally {
    confirming.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="任务进度" :subtitle="`${progress?.task_no ?? '—'} · ${progress?.task_status ?? ''}`">
      <template v-if="progress?.signoff_voucher && !progress.signoff_confirmation" #actions>
        <el-button type="primary" :loading="confirming" @click="confirmOpen = true">确认完成</el-button>
      </template>
    </PageHeader>

    <template v-if="progress">
      <section class="panel">
        <div class="panel-head"><span class="panel-title">任务基本信息</span><span class="panel-hint">进行中任务与关键节点打卡</span></div>
        <div class="panel-body">
          <dl class="kv">
            <dt>任务编号</dt><dd class="num">{{ progress.task_no }}</dd>
            <dt>关联订单</dt><dd class="num">{{ progress.order_no }}</dd>
            <dt>任务状态</dt><dd><StatusPill :text="progress.task_status" /></dd>
            <dt>计划装货</dt><dd class="num">{{ stamp(progress.planned_load_at) }}</dd>
            <dt>计划送达</dt><dd class="num">{{ stamp(progress.planned_deliver_at) }}</dd>
          </dl>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head"><span class="panel-title">执行节点</span><span class="panel-hint">可查看司机提交的打卡与现场照片</span></div>
        <div class="panel-body"><ProcessStepper :steps="steps" /></div>
      </section>

      <section class="panel">
        <div class="panel-head"><span class="panel-title">运输过程时间线</span></div>
        <div class="panel-body">
          <EmptyState v-if="!timeline.length" text="暂无运输过程记录" />
          <ProcessTimeline v-else :items="timeline" />
        </div>
      </section>

      <section v-if="expenses.length" class="panel">
        <div class="panel-head"><span class="panel-title">关联报销费用</span></div>
        <div class="panel-body panel-body--tight">
          <div class="table-wrap">
            <table class="data-table">
              <thead><tr><th class="num">费用编号</th><th>类型</th><th class="num">金额</th><th>审核状态</th><th>支付状态</th><th class="num">提交时间</th></tr></thead>
              <tbody>
                <tr v-for="expense in expenses" :key="expense.id">
                  <td class="num">{{ expense.expense_no }}</td>
                  <td>{{ expense.expense_type }}</td>
                  <td class="num">¥ {{ expense.amount_yuan }}</td>
                  <td><StatusPill :text="displayReview(expense.review_status)" /></td>
                  <td><StatusPill :text="expense.payment_status" /></td>
                  <td class="num">{{ stamp(expense.incurred_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <NoticeBar v-if="progress.signoff_confirmation" tone="info">
        已依据签收凭证确认完成 · {{ stamp(progress.signoff_confirmation.created_at) }}
      </NoticeBar>
    </template>

    <ConfirmDialog v-model="confirmOpen" title="确认完成" confirm-text="确认完成" @confirm="confirm">
      依据司机提交的签收凭证确认任务完成？
    </ConfirmDialog>
  </section>
</template>
