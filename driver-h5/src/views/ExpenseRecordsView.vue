<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { listMyExpenses } from '@/api/expense'
import type { Expense } from '@/types/expense'

const router = useRouter()
const expenses = ref<Expense[]>([])
const loading = ref(false)

onMounted(load)

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
</script>

<template>
  <div class="records-page">
    <header class="topbar">
      <button class="back" type="button" @click="router.replace('/home')">返回</button>
      <span>我的费用记录</span>
    </header>
    <main class="body">
      <p v-if="loading" class="empty">加载中…</p>
      <p v-else-if="expenses.length === 0" class="empty">暂无费用记录</p>
      <article v-for="item in expenses" :key="item.id" class="card">
        <div class="row"><span>{{ item.expense_no }}</span><span>{{ item.task_no }}</span></div>
        <div class="row"><span>类型</span><span>{{ item.expense_type }}</span></div>
        <div class="row"><span>金额</span><span>{{ item.amount_yuan }} 元</span></div>
        <div class="row"><span>发生时间</span><span>{{ item.incurred_at }}</span></div>
        <div class="row"><span>审核状态</span><span>{{ item.review_status }}</span></div>
        <div class="row"><span>支付状态</span><span>{{ item.payment_status }}</span></div>
        <p v-if="item.review_reason" class="reason">驳回原因：{{ item.review_reason }}</p>
        <p class="hint">{{ item.description }} · 凭证 {{ item.vouchers.length }} 张</p>
        <button
          v-if="item.review_status === '审核驳回' && !item.superseded_by"
          class="btn ghost"
          type="button"
          @click="router.push(`/tasks/${item.task_id}/expense`)"
        >
          前往重新提交
        </button>
      </article>
    </main>
  </div>
</template>

<style scoped>
.records-page { display: flex; flex-direction: column; min-height: 100vh; }
.topbar { display: flex; align-items: center; justify-content: space-between; padding: var(--space-4); background: var(--color-surface); border-bottom: 1px solid var(--color-border); font-size: var(--font-size-md); }
.back { min-height: var(--tap-min); padding: 0 var(--space-2); font: inherit; color: var(--color-text); background: transparent; border: 0; }
.body { flex: 1; padding: var(--space-4); }
.card { margin-bottom: var(--space-3); padding: var(--space-4); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius); }
.row { display: flex; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-2); font-size: var(--font-size-sm); }
.row > span:first-child { flex-shrink: 0; color: var(--color-text-muted); }
.empty { padding: var(--space-8) var(--space-4); text-align: center; color: var(--color-text-muted); }
.reason { margin: var(--space-1) 0; font-size: var(--font-size-sm); color: var(--color-error); }
.hint { margin: var(--space-2) 0; font-size: var(--font-size-sm); color: var(--color-text-muted); }
.btn { min-height: var(--tap-min); padding: 0 var(--space-4); font: inherit; border-radius: var(--radius); cursor: pointer; }
.btn.ghost { color: var(--color-text); background: var(--color-surface); border: 1px solid var(--color-border); }
</style>
