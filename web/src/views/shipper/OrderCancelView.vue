<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as cancelApi from '@/api/cancel'
import type { CancelOptions, CancelView } from '@/types/cancel'

const route = useRoute()
const orderId = Number(route.params.orderId)
const options = ref<CancelOptions | null>(null)
const view = ref<CancelView | null>(null)
const reason = ref('')
const busy = ref(false)
const loading = ref(false)

const needsReason = computed(() => options.value?.mode === '公司确认')

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    ;[options.value, view.value] = await Promise.all([
      cancelApi.getCancelOptions(orderId),
      cancelApi.getCancelView(orderId),
    ])
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取取消信息失败')
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  if (needsReason.value && !reason.value.trim()) {
    ElMessage.warning('取消原因必填，请说明取消理由')
    return
  }
  const action = options.value?.mode === '直接取消' ? '直接取消该订单' : '提交取消申请并等待物流公司处理'
  try {
    await ElMessageBox.confirm(`确认${action}？取消后不可撤销。`, '申请取消', {
      type: 'warning',
    })
  } catch {
    return
  }
  busy.value = true
  try {
    await cancelApi.applyCancel(orderId, reason.value.trim() || undefined)
    ElMessage.success('取消申请已提交')
    reason.value = ''
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交取消申请失败')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="cancel" v-loading="loading">
    <h1 class="page-title">订单取消</h1>

    <el-alert
      v-if="options && !options.can_cancel"
      class="notice"
      type="warning"
      :closable="false"
      :title="options.message"
      show-icon
    />

    <div v-else-if="options" class="apply-card">
      <p class="mode">取消方式：{{ options.mode }}</p>
      <p class="hint">
        未承接订单可直接取消；已承接或已派单但未起运需写明原因，由物流公司同意后生效。
      </p>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item :label="needsReason ? '取消原因（必填）' : '取消原因（选填）'">
          <el-input
            v-model="reason"
            type="textarea"
            :rows="3"
            maxlength="500"
            :placeholder="needsReason ? '请说明取消原因' : '可补充取消说明'"
          />
        </el-form-item>
        <el-button type="danger" :loading="busy" @click="submit">提交取消申请</el-button>
      </el-form>
    </div>

    <h2 class="section-title">操作留痕</h2>
    <el-table :data="view?.audit ?? []" size="small" empty-text="暂无取消操作记录">
      <el-table-column prop="event" label="事件" width="110" />
      <el-table-column label="操作人">
        <template #default="{ row }">{{ row.actor }} · {{ row.actor_id }}</template>
      </el-table-column>
      <el-table-column label="状态变化" min-width="200">
        <template #default="{ row }">{{ row.from_status }} → {{ row.to_status }}</template>
      </el-table-column>
      <el-table-column prop="reason" label="原因" min-width="180" />
      <el-table-column prop="created_at" label="时间" min-width="180" />
    </el-table>
  </section>
</template>

<style scoped>
.cancel h1 { margin: 0 0 var(--space-4); }
.notice { margin-bottom: var(--space-4); }
.apply-card {
  margin-bottom: var(--space-6);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
.mode { margin: 0 0 var(--space-2); font-weight: 600; }
.hint { margin: 0 0 var(--space-4); color: var(--color-text-muted); font-size: var(--font-size-sm); }
.section-title { margin: var(--space-6) 0 var(--space-2); font-size: var(--font-size-lg); }
</style>
