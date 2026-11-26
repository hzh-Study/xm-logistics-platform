<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as cancelApi from '@/api/cancel'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import StatusPill from '@/components/StatusPill.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { CancelApplication, CancelView } from '@/types/cancel'

const applications = ref<CancelApplication[]>([])
const loading = ref(false)
const detail = ref<CancelView | null>(null)
const detailOpen = ref(false)
const rejectTarget = ref<CancelApplication | null>(null)
const rejectOpen = ref(false)
const rejectReason = ref('')
const rejectError = ref('')
const agreeTarget = ref<CancelApplication | null>(null)
const agreeOpen = ref(false)
const busy = ref(false)
const orderKeyword = ref('')
const actorKeyword = ref('')

function stamp(value: string | null): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

const filtered = () => applications.value.filter((item) =>
  (!orderKeyword.value || item.order_no.includes(orderKeyword.value)) &&
  (!actorKeyword.value || item.reason.includes(actorKeyword.value)),
)

async function load(): Promise<void> {
  loading.value = true
  try {
    applications.value = await cancelApi.listCancelApplications()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取取消申请失败')
  } finally {
    loading.value = false
  }
}

async function openDetail(application: CancelApplication): Promise<void> {
  try {
    detail.value = await cancelApi.getCancelApplication(application.id)
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取取消留痕失败')
  }
}

async function agree(): Promise<void> {
  const target = agreeTarget.value
  if (!target) return
  busy.value = true
  try {
    await cancelApi.agreeCancel(target.id)
    ElMessage.success('已同意取消，订单已取消')
    detailOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '同意取消失败')
  } finally {
    busy.value = false
  }
}

function openReject(target: CancelApplication): void {
  rejectTarget.value = target
  rejectOpen.value = true
  rejectReason.value = ''
  rejectError.value = ''
}

function askAgree(target: CancelApplication): void {
  agreeTarget.value = target
  agreeOpen.value = true
}

async function reject(): Promise<void> {
  const target = rejectTarget.value
  if (!target) return
  if (!rejectReason.value.trim()) {
    rejectError.value = '驳回原因为必填项，请说明不同意取消的理由。'
    return
  }
  busy.value = true
  try {
    await cancelApi.rejectCancel(target.id, rejectReason.value.trim())
    ElMessage.success('已驳回取消申请，订单已恢复')
    rejectTarget.value = null
    rejectOpen.value = false
    detailOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '驳回取消失败')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="取消申请处理" :subtitle="`待处理 ${applications.filter((item) => item.status === '待公司处理').length} · 已处理 ${applications.filter((item) => item.status !== '待公司处理').length}`" />

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="ca-no">订单编号</label><el-input id="ca-no" v-model="orderKeyword" placeholder="请输入订单编号" clearable /></div>
        <div class="field"><label class="field__label" for="ca-reason">申请原因</label><el-input id="ca-reason" v-model="actorKeyword" placeholder="关键词" clearable /></div>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">取消申请列表</span><span class="panel-hint">货主对已承接未起运订单提交的取消申请 · 需给出处理结果</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!filtered().length" text="暂无取消申请" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">订单编号</th><th>货主 / 货物</th><th>申请原因</th><th>订单状态</th><th class="num">申请时间</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in filtered()" :key="row.id">
                <td class="num">{{ row.order_no }}</td>
                <td>货主 #{{ row.shipper_id }}<div class="cell-sub">{{ row.application_no }}</div></td>
                <td>{{ row.reason }}</td>
                <td><StatusPill :text="row.status" /></td>
                <td class="num">{{ stamp(row.created_at) }}</td>
                <td class="ops">
                  <el-button v-if="row.status === '待公司处理'" type="primary" link @click="openDetail(row)">审核</el-button>
                  <el-button type="primary" link @click="openDetail(row)">查看详情</el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ filtered().length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="detailOpen" title="取消申请审核">
      <template #body>
        <template v-if="detail?.application">
          <NoticeBar tone="info">申请通过后订单变为「已取消」；驳回后恢复申请前状态，驳回原因作为追加记录展示给货主。</NoticeBar>
          <dl class="kv section-gap">
            <dt>订单编号</dt><dd class="num">{{ detail.application.order_no }}</dd>
            <dt>货主</dt><dd>货主 #{{ detail.application.shipper_id }}</dd>
            <dt>申请原因</dt><dd>{{ detail.application.reason }}</dd>
            <dt>申请时间</dt><dd class="num">{{ stamp(detail.application.created_at) }}</dd>
            <dt>当前状态</dt><dd><StatusPill :text="detail.application.status" /></dd>
          </dl>
          <div v-if="detail.audit.length" class="records">
            <h3 class="records-title">留痕</h3>
            <ul class="record-list">
              <li v-for="item in detail.audit" :key="item.id">
                <StatusPill :text="item.event" />
                <span>{{ item.from_status }} → {{ item.to_status }}</span>
                <span class="record-meta">{{ item.actor }} · {{ stamp(item.created_at) }}</span>
              </li>
            </ul>
          </div>
        </template>
      </template>
      <template #footer>
        <template v-if="detail?.application?.status === '待公司处理'">
          <el-button @click="detailOpen = false">关闭</el-button>
          <el-button type="danger" @click="openReject(detail.application)">驳回申请</el-button>
          <el-button type="primary" :loading="busy" @click="askAgree(detail.application)">同意取消</el-button>
        </template>
        <el-button v-else @click="detailOpen = false">关闭</el-button>
      </template>
    </DetailDrawer>

    <ConfirmDialog v-model="agreeOpen" title="同意取消" confirm-text="同意取消" @confirm="agree">
      同意取消运输订单 {{ agreeTarget?.order_no }}？订单将置为「已取消」。
    </ConfirmDialog>

    <DetailDrawer v-model="rejectOpen" title="驳回取消申请">
      <template #body>
        <div class="field">
          <label class="field__label" for="ca-reject"><span class="field__req">*</span>驳回原因</label>
          <el-input id="ca-reject" v-model="rejectReason" type="textarea" :rows="4" placeholder="请说明不同意取消的理由" />
          <p v-if="rejectError" class="field__error">{{ rejectError }}</p>
        </div>
      </template>
      <template #footer>
        <el-button @click="rejectOpen = false">取消</el-button>
        <el-button type="danger" :loading="busy" @click="reject">确认驳回</el-button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.section-gap { margin-top: var(--space-4); }
.records { margin-top: var(--space-5); }
.records-title { margin: 0 0 var(--space-2); font-size: var(--font-size-sm); font-weight: 600; }
.record-list { margin: 0; padding: 0; list-style: none; }
.record-list li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3); padding: var(--space-2) 0; border-bottom: 1px solid var(--color-border); font-size: var(--font-size-sm); }
.record-list li:last-child { border-bottom: 0; }
.record-meta { color: var(--color-text-3); font-size: var(--font-size-xs); }
</style>
