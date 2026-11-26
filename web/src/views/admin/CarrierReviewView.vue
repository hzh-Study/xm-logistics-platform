<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchCarrierCertifications, listCarriers, reviewCertification, setCarrierAccountStatus } from '@/api/admin'
import { ApiError } from '@/api/request'
import PageHeader from '@/components/PageHeader.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import PhotoGrid from '@/components/PhotoGrid.vue'
import type { CarrierSummary, CertificationRecord } from '@/types/carrier'

const carriers = ref<CarrierSummary[]>([])
const history = ref<CertificationRecord[]>([])
const selected = ref<CarrierSummary | null>(null)
const detailOpen = ref(false)
const reason = ref('')
const reasonError = ref('')
const loading = ref(false)
const acting = ref(false)

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    carriers.value = await listCarriers()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取物流公司列表失败')
  } finally {
    loading.value = false
  }
}

async function openDetail(row: CarrierSummary): Promise<void> {
  selected.value = row
  reason.value = ''
  reasonError.value = ''
  try {
    history.value = await fetchCarrierCertifications(row.account_id)
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取认证记录失败')
  }
}

async function review(decision: '审核通过' | '审核不通过'): Promise<void> {
  if (!selected.value) return
  if (decision === '审核不通过' && !reason.value.trim()) {
    reasonError.value = '驳回原因为必填项，请说明驳回理由。'
    return
  }
  acting.value = true
  try {
    await reviewCertification(selected.value.account_id, decision, reason.value.trim())
    ElMessage.success(decision === '审核通过' ? '已通过认证' : '已驳回认证')
    await Promise.all([load(), openDetail(selected.value)])
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '审核失败')
  } finally {
    acting.value = false
  }
}

async function toggleStatus(): Promise<void> {
  if (!selected.value) return
  const next = selected.value.account_status === '已禁用' ? '正常使用' : '已禁用'
  acting.value = true
  try {
    await setCarrierAccountStatus(selected.value.account_id, next)
    ElMessage.success(next === '已禁用' ? '账号已禁用' : '账号已恢复')
    await Promise.all([load(), openDetail(selected.value)])
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  } finally {
    acting.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="公司认证审核" subtitle="仅处理物流公司企业认证 · 营业执照与资质资料" />

    <section class="panel">
      <div class="panel-head"><span class="panel-title">审核列表</span><span class="panel-hint">共 {{ carriers.length }} 条</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!carriers.length" text="暂无物流公司认证记录" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th class="num">主体编号</th><th>企业名称</th><th class="num">统一社会信用代码</th><th>认证状态</th><th class="ops">操作</th></tr></thead>
            <tbody>
              <tr v-for="row in carriers" :key="row.account_id">
                <td class="num">{{ row.account_id }}</td>
                <td>{{ row.company_name }}</td>
                <td class="num">{{ row.license_no }}</td>
                <td><StatusPill :text="row.auth_status" /></td>
                <td class="ops"><el-button type="primary" link @click="openDetail(row)">{{ row.auth_status === '待审核' ? '审核' : '查看' }}</el-button></td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ carriers.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="detailOpen" :title="`公司认证审核 · ${selected?.company_name ?? ''}`">
      <template #body>
        <template v-if="selected">
          <NoticeBar tone="info">审核通过后资料生效；驳回必须填写原因，原因作为追加记录对该主体可见。</NoticeBar>
          <dl class="kv section-gap">
            <dt>企业名称</dt><dd>{{ selected.company_name }}</dd>
            <dt>统一社会信用代码</dt><dd class="num">{{ selected.license_no }}</dd>
            <dt>认证状态</dt><dd><StatusPill :text="selected.auth_status" /></dd>
            <dt>账号状态</dt><dd><StatusPill :text="selected.account_status" /></dd>
          </dl>
          <template v-if="history.length">
            <div v-for="record in history" :key="record.id" class="record">
              <div class="record-head">
                <StatusPill :text="record.decision || '待审核'" />
                <span class="record-meta">{{ record.actor }} · {{ stamp(record.created_at) }}</span>
              </div>
              <p class="record-text">{{ record.legal_person }} · {{ record.contact_name }} {{ record.contact_phone }}</p>
              <PhotoGrid :photos="[record.license_path, record.qualification_path].filter(Boolean)" />
              <p v-if="record.reason" class="record-reason">驳回原因：{{ record.reason }}</p>
            </div>
          </template>
          <EmptyState v-else text="暂无认证记录" />
          <div class="field section-gap">
            <label class="field__label" for="cr-reason"><span class="field__req">*</span>驳回原因（驳回时必填）</label>
            <el-input id="cr-reason" v-model="reason" type="textarea" :rows="3" />
            <p v-if="reasonError" class="field__error">{{ reasonError }}</p>
          </div>
          <div class="account-ops">
            <el-button @click="toggleStatus">{{ selected.account_status === '已禁用' ? '恢复账号' : '禁用账号' }}</el-button>
          </div>
        </template>
      </template>
      <template #footer>
        <el-button @click="detailOpen = false">关闭</el-button>
        <el-button type="danger" :loading="acting" @click="review('审核不通过')">驳回</el-button>
        <el-button type="primary" :loading="acting" @click="review('审核通过')">通过</el-button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.section-gap { margin-top: var(--space-4); }
.record { padding: var(--space-3) 0; border-bottom: 1px solid var(--color-border); }
.record-head { display: flex; align-items: center; gap: var(--space-3); }
.record-meta { color: var(--color-text-3); font-size: var(--font-size-xs); }
.record-text { margin: var(--space-2) 0 0; font-size: var(--font-size-sm); color: var(--color-text-2); }
.record-reason { margin: var(--space-2) 0 0; font-size: var(--font-size-sm); color: var(--color-error); }
.account-ops { margin-top: var(--space-4); }
</style>
