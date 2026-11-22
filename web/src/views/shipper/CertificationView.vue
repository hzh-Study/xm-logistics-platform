<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as shipperApi from '@/api/shipper'
import { useAuthStore } from '@/stores/auth'
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

// 仅未提交或被驳回时可提交 / 重新提交
const canSubmit = computed(() =>
  ['未提交', '审核不通过'].includes(view.value?.auth_status ?? ''),
)

const statusType = computed(() => {
  const map: Record<string, string> = {
    审核通过: 'success',
    审核不通过: 'danger',
    待审核: 'warning',
    未提交: 'info',
  }
  return map[view.value?.auth_status ?? ''] ?? 'info'
})

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
  <section class="cert">
    <h1 class="page-title">货主认证</h1>
    <p class="page-note">
      当前认证状态：<el-tag :type="statusType">{{ view?.auth_status ?? '加载中' }}</el-tag>
    </p>

    <div v-if="view?.current?.rejection_reason" class="panel rejection">
      <h2 class="panel-title">审核驳回原因</h2>
      <p class="rejection-text">{{ view.current.rejection_reason }}</p>
      <p class="panel-text">请据此修改资料后重新提交。</p>
    </div>

    <div v-if="view?.current" class="panel">
      <h2 class="panel-title">最近一次提交</h2>
      <dl class="detail">
        <dt>认证类型</dt>
        <dd>{{ view.current.cert_type }}</dd>
        <dt>姓名 / 企业名称</dt>
        <dd>{{ view.current.name }}</dd>
        <dt>证件号码</dt>
        <dd>{{ view.current.id_number }}</dd>
        <dt>联系人电话</dt>
        <dd>{{ view.current.contact_phone }}</dd>
        <dt>审核结果</dt>
        <dd>{{ view.current.status }}</dd>
      </dl>
    </div>

    <div v-if="canSubmit" class="panel">
      <h2 class="panel-title">{{ view?.current ? '重新提交认证资料' : '提交认证资料' }}</h2>
      <form class="cert-form" @submit.prevent="onSubmit">
        <label class="field">
          <span class="field-label">认证类型</span>
          <el-select v-model="form.cert_type">
            <el-option label="个人" value="个人" />
            <el-option label="企业" value="企业" />
          </el-select>
        </label>
        <label class="field">
          <span class="field-label">姓名 / 企业名称</span>
          <el-input v-model="form.name" placeholder="请输入姓名或企业名称" />
        </label>
        <label class="field">
          <span class="field-label">证件号码</span>
          <el-input v-model="form.id_number" placeholder="身份证号或统一社会信用代码" />
        </label>
        <label class="field">
          <span class="field-label">联系人电话</span>
          <el-input v-model="form.contact_phone" placeholder="请输入联系人电话" />
        </label>
        <label class="field">
          <span class="field-label">资料路径（每行一个相对路径）</span>
          <el-input v-model="documentsText" type="textarea" :rows="3" placeholder="certs/id-front.png" />
        </label>
        <el-button type="primary" native-type="submit" :loading="saving">提交审核</el-button>
      </form>
    </div>

    <p v-else-if="view?.auth_status === '审核通过'" class="panel-text">认证已通过，可发布运输订单。</p>
    <p v-else-if="view?.auth_status === '待审核'" class="panel-text">资料审核中，请耐心等待。</p>
  </section>
</template>

<style scoped>
.cert {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.page-note {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: var(--space-1) 0 var(--space-6);
  color: var(--color-text-muted);
}

.panel {
  margin-bottom: var(--space-4);
  padding: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.panel-title {
  margin: 0 0 var(--space-3);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.panel-text {
  margin: var(--space-2) 0 0;
  color: var(--color-text-muted);
}

.rejection {
  border-color: var(--color-error);
}

.rejection-text {
  margin: 0;
  font-weight: 600;
}

.detail {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: var(--space-2);
  margin: 0;
}

.detail dt {
  color: var(--color-text-muted);
}

.detail dd {
  margin: 0;
}

.field {
  display: block;
  margin-bottom: var(--space-4);
}

.field-label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}
</style>
