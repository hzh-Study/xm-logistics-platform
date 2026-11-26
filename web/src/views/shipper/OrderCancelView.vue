<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as cancelApi from '@/api/cancel'
import PageHeader from '@/components/PageHeader.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { CancelOptions, CancelView } from '@/types/cancel'

const route = useRoute()
const orderId = Number(route.params.orderId)
const options = ref<CancelOptions | null>(null)
const view = ref<CancelView | null>(null)
const reason = ref('')
const reasonError = ref('')
const busy = ref(false)
const loading = ref(false)
const confirmOpen = ref(false)

const needsReason = computed(() => options.value?.mode === '公司确认')

function time(value: string | null): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

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

function openConfirm(): void {
  reasonError.value = ''
  if (needsReason.value && !reason.value.trim()) {
    reasonError.value = '取消原因为必填项，请说明具体原因。'
    return
  }
  confirmOpen.value = true
}

async function submit(): Promise<void> {
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

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="订单取消" subtitle="取消申请 · 原因必填" />

    <NoticeBar v-if="options && !options.can_cancel" tone="warning">{{ options.message }}</NoticeBar>

    <template v-else-if="options">
      <NoticeBar tone="info">
        订单已承接但尚未起运，提交后订单进入「取消处理中」，由物流公司确认后变为「已取消」；如被驳回则恢复原状态并展示驳回原因。
      </NoticeBar>

      <div class="panel-gap" />

      <section class="panel">
        <div class="panel-head"><span class="panel-title">订单摘要</span></div>
        <div class="panel-body">
          <dl class="kv">
            <dt>订单编号</dt><dd class="num">{{ view?.application?.order_no ?? '—' }}</dd>
            <dt>当前状态</dt><dd><StatusPill :text="options.status ?? '—'" /></dd>
            <dt>货物</dt><dd>{{ view?.application?.reason ? '见申请原因' : '—' }}</dd>
            <dt>申请时间</dt><dd class="num">{{ time(view?.application?.created_at ?? null) }}</dd>
          </dl>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head"><span class="panel-title">取消申请</span></div>
        <div class="panel-body">
          <div class="field">
            <label class="field__label" for="cancel-reason">
              <span v-if="needsReason" class="field__req">*</span>{{ needsReason ? '取消原因' : '补充说明' }}
            </label>
            <el-input
              id="cancel-reason"
              v-model="reason"
              type="textarea"
              :rows="4"
              maxlength="500"
              :placeholder="needsReason ? '请说明取消原因' : '可补充取消说明'"
              :class="{ 'is-error': reasonError }"
            />
            <p v-if="reasonError" class="field__error">{{ reasonError }}</p>
            <p v-else class="field__help">取消原因为必填项，请说明具体原因。</p>
          </div>
          <div class="form-actions">
            <el-button @click="$router.push('/shipper/orders')">返回</el-button>
            <el-button type="danger" :loading="busy" @click="openConfirm">提交取消申请</el-button>
          </div>
        </div>
      </section>
    </template>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">操作留痕</span></div>
      <div class="panel-body">
        <EmptyState v-if="!view?.audit.length" text="暂无取消操作记录" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th>事件</th><th>操作人</th><th>状态变化</th><th>原因</th><th class="num">时间</th></tr></thead>
            <tbody>
              <tr v-for="item in view.audit" :key="item.id">
                <td>{{ item.event }}</td>
                <td>{{ item.actor }} · {{ item.actor_id }}</td>
                <td>{{ item.from_status }} → {{ item.to_status }}</td>
                <td>{{ item.reason || '—' }}</td>
                <td class="num">{{ time(item.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <ConfirmDialog
      v-model="confirmOpen"
      title="确认提交取消申请"
      confirm-text="确认提交"
      danger
      @confirm="submit"
    >
      提交后订单状态变为「取消处理中」，等待物流公司处理，期间不可重复提交。
    </ConfirmDialog>
  </section>
</template>

<style scoped>
.panel-gap { height: var(--space-4); }
.is-error :deep(.el-textarea__inner) { border-color: var(--color-error); }
</style>
