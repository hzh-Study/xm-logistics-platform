<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import PageHeader from '@/components/PageHeader.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import PhotoGrid from '@/components/PhotoGrid.vue'
import type { AdminCertification } from '@/types/shipper'

const rows = ref<AdminCertification[]>([])
const loading = ref(false)
const saving = ref(false)
const detailOpen = ref(false)
const current = ref<AdminCertification | null>(null)
const reason = ref('')
const reasonError = ref('')

function stamp(value: string | null): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function failure(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await adminApi.fetchShipperCertifications()
  } catch (error) {
    ElMessage.error(failure(error))
  } finally {
    loading.value = false
  }
}

function openDetail(row: AdminCertification): void {
  current.value = row
  reason.value = ''
  reasonError.value = ''
  detailOpen.value = true
}

async function approve(): Promise<void> {
  const row = current.value
  if (!row?.certification_id) return
  saving.value = true
  try {
    await adminApi.reviewShipperCertification(row.certification_id, '审核通过')
    ElMessage.success('已审核通过')
    detailOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(failure(error))
  } finally {
    saving.value = false
  }
}

async function reject(): Promise<void> {
  const row = current.value
  if (!row?.certification_id) return
  if (!reason.value.trim()) {
    reasonError.value = '驳回原因为必填项，请说明驳回理由。'
    return
  }
  saving.value = true
  try {
    await adminApi.reviewShipperCertification(row.certification_id, '审核不通过', reason.value.trim())
    ElMessage.success('已驳回')
    detailOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(failure(error))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="货主认证审核" subtitle="仅处理货主认证 · 个人 / 企业两类资料" />

    <section class="panel">
      <div class="panel-head"><span class="panel-title">审核列表</span><span class="panel-hint">共 {{ rows.length }} 条</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!rows.length" text="暂无货主认证记录" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th class="num">主体编号</th><th>主体名称</th><th>主体类型</th><th class="num">提交时间</th><th>认证状态</th><th class="ops">操作</th></tr></thead>
            <tbody>
              <tr v-for="row in rows" :key="row.account_id">
                <td class="num">{{ row.account_id }}</td>
                <td>{{ row.name }}</td>
                <td>{{ row.cert_type || '—' }}</td>
                <td class="num">{{ stamp(row.submitted_at) }}</td>
                <td><StatusPill :text="row.status || row.auth_status" /></td>
                <td class="ops"><el-button type="primary" link @click="openDetail(row)">{{ row.status === '待审核' ? '审核' : '查看' }}</el-button></td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ rows.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="detailOpen" :title="`认证审核详情 · ${current?.name ?? ''}`">
      <template #body>
        <template v-if="current">
          <NoticeBar tone="info">审核通过后资料生效；驳回必须填写原因，原因作为追加记录对该主体可见。</NoticeBar>
          <dl class="kv section-gap">
            <dt>主体名称</dt><dd>{{ current.name }}</dd>
            <dt>认证类型</dt><dd>{{ current.cert_type }}</dd>
            <dt>证件号码</dt><dd class="num">{{ current.id_number }}</dd>
            <dt>联系人 / 电话</dt><dd class="num">{{ current.contact_phone }}</dd>
            <dt>提交时间</dt><dd class="num">{{ stamp(current.submitted_at) }}</dd>
            <dt>审核结果</dt><dd><StatusPill :text="current.status || current.auth_status" /></dd>
            <dt v-if="current.rejection_reason">驳回原因</dt><dd v-if="current.rejection_reason">{{ current.rejection_reason }}</dd>
          </dl>
          <PhotoGrid v-if="current.documents.length" :photos="current.documents" />
          <div class="field section-gap">
            <label class="field__label" for="sc-reason"><span class="field__req">*</span>驳回原因（驳回时必填）</label>
            <el-input id="sc-reason" v-model="reason" type="textarea" :rows="3" />
            <p v-if="reasonError" class="field__error">{{ reasonError }}</p>
          </div>
        </template>
      </template>
      <template #footer>
        <el-button @click="detailOpen = false">关闭</el-button>
        <el-button type="danger" :loading="saving" @click="reject">驳回</el-button>
        <el-button type="primary" :loading="saving" @click="approve">通过</el-button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.section-gap { margin-top: var(--space-4); }
</style>
