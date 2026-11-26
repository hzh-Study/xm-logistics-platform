<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { listMyExpenses } from '@/api/expense'
import H5PageHeader from '@/components/H5PageHeader.vue'
import H5Card from '@/components/H5Card.vue'
import H5EmptyState from '@/components/H5EmptyState.vue'
import H5BottomBar from '@/components/H5BottomBar.vue'
import H5Notice from '@/components/H5Notice.vue'
import type { Expense } from '@/types/expense'

const router = useRouter()
const expenses = ref<Expense[]>([])
const loading = ref(false)
const activeTab = ref(0)
const tabs = ['全部', '待审核', '已通过', '已驳回'] as const

const filtered = computed(() => expenses.value.filter((item) => {
  const tab = tabs[activeTab.value]
  if (tab === '全部') return true
  if (tab === '待审核') return item.review_status === '待审核'
  if (tab === '已通过') return item.review_status === '审核通过'
  return item.review_status === '审核驳回'
}))

function displayReview(status: string): string {
  return status === '审核驳回' ? '审核不通过' : status
}

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function tone(status: string): string {
  if (status === '审核通过' || status === '已支付') return 'brand'
  if (status === '审核驳回') return 'error'
  return 'warning'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    expenses.value = await listMyExpenses()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '读取费用记录失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="h5-page h5-page--with-bar">
    <H5PageHeader title="费用记录" />
    <main class="h5-scroll">
      <van-tabs v-model:active="activeTab" color="var(--color-accent)" title-active-color="var(--color-accent)">
        <van-tab v-for="tab in tabs" :key="tab" :title="tab" />
      </van-tabs>

      <H5EmptyState v-if="!filtered.length" text="暂无该状态的报销费用" />
      <H5Card v-for="item in filtered" :key="item.id">
        <div class="er-head">
          <span class="er-type">{{ item.expense_type }}</span>
          <span class="er-amount h5-num">¥ {{ item.amount_yuan }}</span>
        </div>
        <p class="er-no h5-num">{{ item.expense_no }} · {{ stamp(item.incurred_at) }}</p>
        <div class="h5-row"><span class="k">审核状态</span><span class="v" :class="`er-status--${tone(item.review_status)}`">{{ displayReview(item.review_status) }}</span></div>
        <div class="h5-row"><span class="k">支付状态</span><span class="v" :class="`er-status--${tone(item.payment_status)}`">{{ item.payment_status }}</span></div>
        <div class="h5-row"><span class="k">关联任务</span><span class="v h5-num">{{ item.task_no }}</span></div>
        <H5Notice v-if="item.review_reason" tone="error">驳回原因：{{ item.review_reason }}</H5Notice>
        <div v-if="item.review_status === '审核驳回'" class="er-actions">
          <van-button size="small" type="primary" @click="router.push(`/tasks/${item.task_id}/expense`)">重新提交</van-button>
        </div>
      </H5Card>
    </main>

    <H5BottomBar>
      <van-button block type="primary" @click="router.push('/tasks')">提交新费用</van-button>
    </H5BottomBar>
  </div>
</template>

<style scoped>
.er-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.er-type { font-size: var(--font-size-md); font-weight: 600; }
.er-amount { font-size: var(--font-size-lg); font-weight: 600; }
.er-no { margin: var(--space-1) 0 var(--space-2); font-size: var(--font-size-xs); color: var(--color-text-3); }
.er-status--brand { color: var(--color-accent); }
.er-status--warning { color: var(--color-warning); }
.er-status--error { color: var(--color-error); }
.er-actions { margin-top: var(--space-3); }
</style>
