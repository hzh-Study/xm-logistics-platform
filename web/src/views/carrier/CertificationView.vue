<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import { fetchCapabilities, fetchCertification, submitCertification } from '@/api/carrier'
import PageHeader from '@/components/PageHeader.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import FormSection from '@/components/FormSection.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { Capabilities, CertificationRecord, CertificationSubmitPayload, CertificationView } from '@/types/carrier'

const view = ref<CertificationView | null>(null)
const capabilities = ref<Capabilities | null>(null)
const loading = ref(false)
const submitting = ref(false)

const form = reactive<CertificationSubmitPayload>({
  company_name: '', license_no: '', license_path: '', legal_person: '',
  contact_name: '', contact_phone: '', qualification_path: '', note: '',
})

const rejection = computed(() => {
  const latest = view.value?.latest
  return latest?.decision === '审核不通过' ? latest.reason : ''
})

const blockedReasons = computed(() => capabilities.value?.reasons ?? [])
const canSubmit = computed(() => ['未提交', '审核不通过'].includes(view.value?.auth_status ?? ''))

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    view.value = await fetchCertification()
    capabilities.value = await fetchCapabilities()
    const latest = view.value.latest
    if (latest) {
      Object.assign(form, {
        company_name: latest.company_name, license_no: latest.license_no, license_path: latest.license_path,
        legal_person: latest.legal_person, contact_name: latest.contact_name, contact_phone: latest.contact_phone,
        qualification_path: latest.qualification_path,
      })
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取认证状态失败')
  } finally {
    loading.value = false
  }
}

async function onSubmit(): Promise<void> {
  if (!form.company_name.trim() || !form.license_no.trim() || !form.contact_name.trim() || !form.contact_phone.trim()) {
    ElMessage.warning('请完整填写企业名称、统一社会信用代码、联系人与电话')
    return
  }
  submitting.value = true
  try {
    await submitCertification({ ...form })
    ElMessage.success('认证资料已提交，请等待管理员审核')
    await load()
  } catch (error) {
    if (error instanceof ApiError && Array.isArray(error.details)) {
      const first = error.details[0] as { field?: string; message?: string }
      ElMessage.error(`${first.field ?? '字段'}：${first.message ?? '请检查输入'}`)
    } else {
      ElMessage.error(error instanceof Error ? error.message : '提交失败')
    }
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="企业认证" subtitle="企业资料与资质只读展示" />

    <NoticeBar v-if="rejection" tone="error">审核不通过原因：{{ rejection }}，请修改资料后重新提交。</NoticeBar>
    <NoticeBar v-if="blockedReasons.length" tone="warning">承运业务暂不可用：{{ blockedReasons.join('；') }}。</NoticeBar>

    <NoticeBar v-if="view" :tone="view.auth_status === '审核通过' ? 'info' : 'warning'">
      认证状态：<StatusPill :text="view.auth_status" />
      <template v-if="view.auth_status === '审核通过'">。资料只读；重要信息变更需触发重新认证。</template>
      <template v-else>。审核通过后，订单池承接、派单、司机与车辆管理方可使用。</template>
    </NoticeBar>

    <FormSection title="企业基本信息">
      <template v-if="view?.latest">
        <dl class="kv">
          <dt>认证状态</dt><dd><StatusPill :text="view.auth_status" /></dd>
          <dt>企业名称</dt><dd>{{ view.latest.company_name }}</dd>
          <dt>统一社会信用代码</dt><dd class="num">{{ view.latest.license_no }}</dd>
          <dt>法定代表人</dt><dd>{{ view.latest.legal_person }}</dd>
          <dt>联系人 / 电话</dt><dd class="num">{{ view.latest.contact_name }} / {{ view.latest.contact_phone }}</dd>
          <dt>提交时间</dt><dd class="num">{{ stamp(view.latest.created_at) }}</dd>
        </dl>
        <div class="docs">
          <span>营业执照</span><span class="doc">{{ view.latest.license_path || '—' }}</span>
          <span>道路运输经营许可证</span><span class="doc">{{ view.latest.qualification_path || '—' }}</span>
        </div>
      </template>
      <EmptyState v-else text="暂无企业认证资料" />
    </FormSection>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">认证记录</span></div>
      <div class="panel-body">
        <EmptyState v-if="!view?.records.length" text="暂无认证记录" />
        <ul v-else class="record-list">
          <li v-for="(record, index) in view.records" :key="record.id ?? index">
            <StatusPill :text="record.decision || '待审核'" />
            <span>{{ record.kind }} · {{ record.actor }}</span>
            <span class="record-meta">{{ stamp(record.created_at) }}</span>
            <span v-if="record.reason" class="record-reason">{{ record.reason }}</span>
          </li>
        </ul>
      </div>
    </section>

    <FormSection v-if="canSubmit" :title="view?.latest ? '重新提交企业认证资料' : '提交企业认证资料'">
      <form class="form-grid" @submit.prevent="onSubmit">
        <div class="field"><label class="field__label"><span class="field__req">*</span>企业名称</label><el-input v-model="form.company_name" /></div>
        <div class="field"><label class="field__label"><span class="field__req">*</span>统一社会信用代码</label><el-input v-model="form.license_no" /></div>
        <div class="field"><label class="field__label">法定代表人</label><el-input v-model="form.legal_person" /></div>
        <div class="field"><label class="field__label"><span class="field__req">*</span>联系人</label><el-input v-model="form.contact_name" /></div>
        <div class="field"><label class="field__label"><span class="field__req">*</span>联系电话</label><el-input v-model="form.contact_phone" /></div>
        <div class="field"><label class="field__label">营业执照路径</label><el-input v-model="form.license_path" placeholder="库内相对路径" /></div>
        <div class="field field--wide"><label class="field__label">道路运输经营许可证路径</label><el-input v-model="form.qualification_path" placeholder="库内相对路径" /></div>
        <div class="field field--wide"><label class="field__label">备注</label><el-input v-model="form.note" type="textarea" :rows="2" /></div>
        <div class="field field--wide form-actions"><el-button type="primary" native-type="submit" :loading="submitting">提交审核</el-button></div>
      </form>
    </FormSection>
  </section>
</template>

<style scoped>
.docs { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-4); font-size: var(--font-size-sm); color: var(--color-text-3); }
.doc { padding: 2px 8px; border-radius: var(--radius-control); background: var(--color-fill); }
.record-list { margin: 0; padding: 0; list-style: none; }
.record-list li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3); padding: var(--space-3) 0; border-bottom: 1px solid var(--color-border); }
.record-list li:last-child { border-bottom: 0; }
.record-meta { font-size: var(--font-size-xs); color: var(--color-text-3); }
.record-reason { font-size: var(--font-size-sm); color: var(--color-error); }
.field--wide { grid-column: 1 / -1; }
</style>
