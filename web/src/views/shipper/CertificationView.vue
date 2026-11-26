<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as shipperApi from '@/api/shipper'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/PageHeader.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import FormSection from '@/components/FormSection.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { CertificationInput, CertificationView } from '@/types/shipper'

const auth = useAuthStore()
const view = ref<CertificationView | null>(null)
const loading = ref(false)
const saving = ref(false)
const form = ref<CertificationInput>({
  cert_type: '个人',
  name: '',
  id_number: '',
  contact_phone: '',
  documents: [],
})
const documentsText = ref('')

const canSubmit = computed(() =>
  ['未提交', '审核不通过'].includes(view.value?.auth_status ?? ''),
)

function time(value: string | null): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

function failure(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    view.value = await shipperApi.fetchCertification()
  } catch (error) {
    ElMessage.error(failure(error))
  } finally {
    loading.value = false
  }
}

async function onSubmit(): Promise<void> {
  if (!form.value.name.trim() || !form.value.id_number.trim() || !form.value.contact_phone.trim()) {
    ElMessage.warning('请完整填写名称、证件号码与联系人电话')
    return
  }
  saving.value = true
  try {
    const data: CertificationInput = {
      ...form.value,
      documents: documentsText.value
        .split('\n')
        .map((item) => item.trim())
        .filter((item) => item.length > 0),
    }
    await shipperApi.submitCertification(data)
    ElMessage.success('认证资料已提交，请等待审核')
    await Promise.all([load(), auth.refresh()])
  } catch (error) {
    ElMessage.error(failure(error))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="货主认证" subtitle="认证信息只读展示，业务记录追加式不可改写" />

    <NoticeBar v-if="view?.current?.rejection_reason" tone="error">
      审核驳回原因：{{ view.current.rejection_reason }}，请修改资料后重新提交。
    </NoticeBar>

    <NoticeBar v-if="view" :tone="view.auth_status === '审核通过' ? 'info' : 'warning'">
      认证状态：<StatusPill :text="view.auth_status" />
      <template v-if="view.auth_status === '审核通过'">。审核通过后资料不可自行修改；如需变更，请联系平台管理员。</template>
      <template v-else-if="view.auth_status === '待审核'">。资料审核中，请耐心等待。</template>
    </NoticeBar>

    <FormSection title="企业基本信息">
      <template v-if="view?.current">
        <dl class="kv">
          <dt>认证类型</dt><dd>{{ view.current.cert_type }}</dd>
          <dt>名称</dt><dd>{{ view.current.name }}</dd>
          <dt>证件号码</dt><dd class="num">{{ view.current.id_number }}</dd>
          <dt>联系人电话</dt><dd class="num">{{ view.current.contact_phone }}</dd>
          <dt>提交时间</dt><dd class="num">{{ time(view.current.submitted_at) }}</dd>
          <dt>审核结果</dt><dd><StatusPill :text="view.current.status" /></dd>
        </dl>
        <div v-if="view.current.documents.length" class="docs">
          <span>资料文件</span>
          <span v-for="(doc, index) in view.current.documents" :key="`${doc}-${index}`" class="doc">{{ doc }}</span>
        </div>
      </template>
      <EmptyState v-else text="暂无认证资料" />
    </FormSection>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">认证记录</span></div>
      <div class="panel-body">
        <EmptyState v-if="!view?.history.length" text="暂无认证记录" />
        <ul v-else class="record-list">
          <li v-for="item in view.history" :key="item.id">
            <StatusPill :text="item.status" />
            <span class="record-meta">{{ time(item.submitted_at) }} · {{ item.reviewer_id ? '管理员' : '货主' }}</span>
            <span v-if="item.rejection_reason" class="record-reason">{{ item.rejection_reason }}</span>
          </li>
        </ul>
      </div>
    </section>

    <FormSection v-if="canSubmit" :title="view?.current ? '重新提交认证资料' : '提交认证资料'">
      <form class="form-grid" @submit.prevent="onSubmit">
        <div class="field">
          <label class="field__label" for="cert-type">认证类型</label>
          <el-select id="cert-type" v-model="form.cert_type">
            <el-option label="个人" value="个人" />
            <el-option label="企业" value="企业" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="cert-name"><span class="field__req">*</span>姓名 / 企业名称</label>
          <el-input id="cert-name" v-model="form.name" placeholder="请输入姓名或企业名称" />
        </div>
        <div class="field">
          <label class="field__label" for="cert-id"><span class="field__req">*</span>证件号码</label>
          <el-input id="cert-id" v-model="form.id_number" placeholder="身份证号或统一社会信用代码" />
        </div>
        <div class="field">
          <label class="field__label" for="cert-phone"><span class="field__req">*</span>联系人电话</label>
          <el-input id="cert-phone" v-model="form.contact_phone" placeholder="请输入联系人电话" />
        </div>
        <div class="field field--wide">
          <label class="field__label" for="cert-docs">资料路径（每行一个相对路径）</label>
          <el-input id="cert-docs" v-model="documentsText" type="textarea" :rows="3" placeholder="certs/id-front.png" />
          <p class="field__help">凭证仅存库内相对路径，不上传绝对路径。</p>
        </div>
        <div class="field field--wide form-actions">
          <el-button type="primary" native-type="submit" :loading="saving">提交审核</el-button>
        </div>
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
.record-meta { font-size: var(--font-size-xs); color: var(--color-text-3); font-variant-numeric: tabular-nums; }
.record-reason { font-size: var(--font-size-sm); color: var(--color-error); }
.field--wide { grid-column: 1 / -1; }
</style>
