<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import type { AdminCertification } from '@/types/shipper'

const rows = ref<AdminCertification[]>([])
const loading = ref(false)
const rejectTarget = ref<AdminCertification | null>(null)
const rejectionReason = ref('')
const saving = ref(false)

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

async function approve(row: AdminCertification): Promise<void> {
  if (!row.certification_id) return
  try {
    await adminApi.reviewShipperCertification(row.certification_id, '审核通过')
    ElMessage.success('已审核通过')
    await load()
  } catch (error) {
    ElMessage.error(failure(error))
  }
}

function openReject(row: AdminCertification): void {
  rejectTarget.value = row
  rejectionReason.value = ''
}

async function confirmReject(): Promise<void> {
  const target = rejectTarget.value
  if (!target?.certification_id) return
  if (!rejectionReason.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  saving.value = true
  try {
    await adminApi.reviewShipperCertification(
      target.certification_id,
      '审核不通过',
      rejectionReason.value.trim(),
    )
    ElMessage.success('已驳回')
    rejectTarget.value = null
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
  <section class="reviews">
    <h1 class="page-title">货主认证审核</h1>
    <el-table :data="rows" v-loading="loading" row-key="account_id">
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="cert_type" label="认证类型" />
      <el-table-column prop="name" label="姓名 / 企业名称" />
      <el-table-column prop="status" label="审核状态" />
      <el-table-column prop="rejection_reason" label="驳回原因" />
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button
            v-if="row.certification_id && row.status === '待审核'"
            type="primary"
            link
            @click="approve(row)"
          >
            审核通过
          </el-button>
          <el-button
            v-if="row.certification_id && row.status === '待审核'"
            type="danger"
            link
            @click="openReject(row)"
          >
            驳回
          </el-button>
          <span v-if="!row.certification_id">未提交</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="rejectTarget" title="驳回认证" width="420px">
      <label class="field">
        <span class="field-label">驳回原因（必填，货主可见）</span>
        <el-input v-model="rejectionReason" type="textarea" :rows="3" placeholder="请说明需要补正的内容" />
      </label>
      <template #footer>
        <el-button @click="rejectTarget = null">取消</el-button>
        <el-button type="danger" :loading="saving" @click="confirmReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.reviews {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0 0 var(--space-6);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.field {
  display: block;
}

.field-label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}
</style>
