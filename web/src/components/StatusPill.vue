<script setup lang="ts">
import { computed } from 'vue'

type Tone = 'neutral' | 'brand' | 'success' | 'warning' | 'error'

interface Props {
  text: string
  tone?: Tone
}

const { text, tone } = defineProps<Props>()

const BRAND = new Set(['已承接', '运输中', '待派单'])
const SUCCESS = new Set(['审核通过', '正常使用', '已完成', '可派单', '在职', '可用', '在册', '已支付', '启用', '正常', '有效'])
const WARNING = new Set([
  '待审核', '待承接', '取消处理中', '待司机确认', '待装货', '待签收', '待确认完成',
  '任务占用中', '暂停接单', '维修中', '占用中', '暂停使用', '待支付', '草稿',
])
const ERROR = new Set([
  '审核不通过', '审核驳回', '已禁用', '已取消', '异常处理中', '异常', '已拒绝',
  '离职', '已停用', '停用', '已过期',
])

const resolvedTone = computed<Tone>(() => {
  if (tone) return tone
  if (BRAND.has(text)) return 'brand'
  if (SUCCESS.has(text)) return 'success'
  if (WARNING.has(text)) return 'warning'
  if (ERROR.has(text)) return 'error'
  return 'neutral'
})
</script>

<template>
  <span class="status-pill" :class="`status-pill--${resolvedTone}`">{{ text }}</span>
</template>

<style scoped>
.status-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 9px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  line-height: 1;
  font-weight: 500;
  white-space: nowrap;
  background: var(--color-fill);
  color: var(--color-text-2);
}
.status-pill--brand { background: var(--color-accent-soft); color: var(--color-accent); }
.status-pill--success { background: var(--color-success-soft); color: var(--color-success); }
.status-pill--warning { background: var(--color-warning-soft); color: var(--color-warning); }
.status-pill--error { background: var(--color-error-soft); color: var(--color-error); }
</style>
