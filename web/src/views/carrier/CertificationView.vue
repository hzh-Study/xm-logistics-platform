<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import {
  fetchCapabilities,
  fetchCertification,
  submitCertification,
} from '@/api/carrier'
import type {
  Capabilities,
  CertificationRecord,
  CertificationSubmitPayload,
  CertificationView,
} from '@/types/carrier'

const view = ref<CertificationView | null>(null)
const capabilities = ref<Capabilities | null>(null)
const loading = ref(false)
const submitting = ref(false)

const form = reactive<CertificationSubmitPayload>({
  company_name: '',
  license_no: '',
  license_path: '',
  legal_person: '',
  contact_name: '',
  contact_phone: '',
  qualification_path: '',
  note: '',
})

const rejection = computed(() => {
  const latest = view.value?.latest
  return latest?.decision === '驳回' ? latest.reason : ''
})

const blockedReasons = computed(() => capabilities.value?.reasons ?? [])

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    view.value = await fetchCertification()
    capabilities.value = await fetchCapabilities()
    const latest = view.value.latest
    if (latest) {
      form.company_name = latest.company_name
      form.license_no = latest.license_no
      form.license_path = latest.license_path
      form.legal_person = latest.legal_person
      form.contact_name = latest.contact_name
      form.contact_phone = latest.contact_phone
      form.qualification_path = latest.qualification_path
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取认证状态失败')
  } finally {
    loading.value = false
  }
}

async function onSubmit(): Promise<void> {
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
</script>

<template>
  <section class="certification">
    <h1 class="page-title">企业认证</h1>
    <p class="page-note">提交企业资料后由平台审核，通过后方可承接运输订单与派单。</p>

    <div class="status-row">
      <span class="field-label">当前认证状态</span>
      <el-tag type="info" effect="light">{{ view?.auth_status ?? '读取中' }}</el-tag>
    </div>

    <el-alert
      v-if="rejection"
      class="notice"
      type="error"
      :closable="false"
      title="管理员驳回原因"
      :description="rejection"
    />
    <el-alert
      v-for="reason in blockedReasons"
      :key="reason"
      class="notice"
      type="warning"
      :closable="false"
      title="承运业务暂不可用"
      :description="reason"
    />

    <div class="panel form-panel">
      <h2 class="panel-title">企业认证资料</h2>
      <el-form :model="form" label-width="120px" v-loading="loading">
        <el-form-item label="企业名称" required>
          <el-input v-model="form.company_name" maxlength="128" />
        </el-form-item>
        <el-form-item label="营业执照号" required>
          <el-input v-model="form.license_no" maxlength="64" />
        </el-form-item>
        <el-form-item label="营业执照凭证路径" required>
          <el-input v-model="form.license_path" maxlength="512" />
        </el-form-item>
        <el-form-item label="负责人" required>
          <el-input v-model="form.legal_person" maxlength="64" />
        </el-form-item>
        <el-form-item label="联系人" required>
          <el-input v-model="form.contact_name" maxlength="64" />
        </el-form-item>
        <el-form-item label="联系电话" required>
          <el-input v-model="form.contact_phone" maxlength="64" />
        </el-form-item>
        <el-form-item label="资质资料路径" required>
          <el-input v-model="form.qualification_path" maxlength="512" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" maxlength="1000" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="onSubmit">
            提交认证资料
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="panel">
      <h2 class="panel-title">认证记录</h2>
      <p v-if="!view?.records.length" class="empty">暂无认证记录，提交后记录将在此按时间追加。</p>
      <el-table v-else :data="view.records" border>
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column prop="kind" label="类型" width="90" />
        <el-table-column prop="decision" label="结论" width="90" />
        <el-table-column prop="actor" label="操作角色" width="100" />
        <el-table-column prop="company_name" label="企业名称" />
        <el-table-column prop="reason" label="驳回原因">
          <template #default="{ row }: { row: CertificationRecord }">
            {{ row.reason || '—' }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </section>
</template>

<style scoped>
.certification {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.page-note {
  margin: var(--space-1) 0 var(--space-6);
  color: var(--color-text-muted);
}

.status-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.field-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.notice {
  margin-bottom: var(--space-3);
}

.panel {
  padding: var(--space-6);
  margin-bottom: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.panel-title {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.form-panel {
  max-width: 720px;
}

.empty {
  color: var(--color-text-muted);
}
</style>
