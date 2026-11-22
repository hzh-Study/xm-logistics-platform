<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchCarrierCertifications,
  listCarriers,
  reviewCertification,
  setCarrierAccountStatus,
} from '@/api/admin'
import { ApiError } from '@/api/request'
import type { CarrierSummary, CertificationRecord } from '@/types/carrier'

const carriers = ref<CarrierSummary[]>([])
const history = ref<CertificationRecord[]>([])
const selected = ref<CarrierSummary | null>(null)
const reason = ref('')
const loading = ref(false)
const acting = ref(false)

onMounted(loadCarriers)

async function loadCarriers(): Promise<void> {
  loading.value = true
  try {
    carriers.value = await listCarriers()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取物流公司列表失败')
  } finally {
    loading.value = false
  }
}

async function onSelect(row: CarrierSummary): Promise<void> {
  selected.value = row
  reason.value = ''
  try {
    history.value = await fetchCarrierCertifications(row.account_id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取认证记录失败')
  }
}

async function onReview(decision: '审核通过' | '审核不通过'): Promise<void> {
  if (!selected.value) return
  if (decision === '审核不通过' && !reason.value.trim()) {
    ElMessage.error('驳回原因必填')
    return
  }
  acting.value = true
  try {
    await reviewCertification(selected.value.account_id, decision, reason.value.trim())
    ElMessage.success(decision === '审核通过' ? '已通过认证' : '已驳回认证')
    await Promise.all([loadCarriers(), onSelect(selected.value)])
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '审核失败')
  } finally {
    acting.value = false
  }
}

async function onToggleStatus(): Promise<void> {
  if (!selected.value) return
  const next = selected.value.account_status === '已禁用' ? '正常使用' : '已禁用'
  acting.value = true
  try {
    await setCarrierAccountStatus(selected.value.account_id, next)
    ElMessage.success(next === '已禁用' ? '账号已禁用' : '账号已恢复')
    await loadCarriers()
    await onSelect(selected.value)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  } finally {
    acting.value = false
  }
}
</script>

<template>
  <section class="review">
    <h1 class="page-title">物流公司认证审核</h1>
    <p class="page-note">审核企业认证资料；驳回须填写公司可见的原因，审核记录只读追加。</p>

    <div class="panel">
      <h2 class="panel-title">物流公司列表</h2>
      <el-table
        v-loading="loading"
        :data="carriers"
        border
        highlight-current-row
        @current-change="onSelect"
      >
        <el-table-column prop="company_name" label="企业名称" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="license_no" label="营业执照号" width="200" />
        <el-table-column prop="auth_status" label="认证状态" width="120" />
        <el-table-column prop="account_status" label="账号状态" width="120" />
      </el-table>
    </div>

    <div v-if="selected" class="panel">
      <h2 class="panel-title">{{ selected.company_name }} · 认证记录</h2>
      <p v-if="!history.length" class="empty">该公司尚未提交认证资料。</p>
      <el-table v-else :data="history" border>
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column prop="kind" label="类型" width="90" />
        <el-table-column prop="decision" label="结论" width="90" />
        <el-table-column prop="company_name" label="企业名称" />
        <el-table-column prop="license_no" label="营业执照号" width="200" />
        <el-table-column prop="reason" label="驳回原因" />
      </el-table>

      <div class="actions">
        <label class="field">
          <span class="field-label">驳回原因（驳回时必填）</span>
          <el-input v-model="reason" type="textarea" maxlength="1000" rows="2" />
        </label>
        <div class="buttons">
          <el-button type="success" :loading="acting" @click="onReview('审核通过')">审核通过</el-button>
          <el-button type="danger" :loading="acting" @click="onReview('审核不通过')">审核不通过</el-button>
          <el-button :loading="acting" @click="onToggleStatus">
            {{ selected.account_status === '已禁用' ? '恢复账号' : '禁用账号' }}
          </el-button>
        </div>
      </div>
    </div>
    <div v-else class="panel empty">从列表中选择一家物流公司进行审核。</div>
  </section>
</template>

<style scoped>
.review {
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

.actions {
  margin-top: var(--space-6);
}

.field {
  display: block;
  max-width: 640px;
}

.field-label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.buttons {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.empty {
  color: var(--color-text-muted);
}
</style>
