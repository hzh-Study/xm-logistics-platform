<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as cancelApi from '@/api/cancel'
import type { CancelApplication, CancelView } from '@/types/cancel'

const applications = ref<CancelApplication[]>([])
const loading = ref(false)
const detail = ref<CancelView | null>(null)
const rejectTarget = ref<CancelApplication | null>(null)
const rejectReason = ref('')
const busy = ref(false)

onMounted(load)

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
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取取消留痕失败')
  }
}

async function agree(application: CancelApplication): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `同意取消运输订单 ${application.order_no}？订单将置为已取消。`,
      '同意取消',
      { type: 'warning' },
    )
  } catch {
    return
  }
  busy.value = true
  try {
    await cancelApi.agreeCancel(application.id)
    ElMessage.success('已同意取消，订单已取消')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '同意取消失败')
  } finally {
    busy.value = false
  }
}

async function reject(): Promise<void> {
  const target = rejectTarget.value
  if (!target) return
  if (!rejectReason.value.trim()) {
    ElMessage.warning('驳回原因必填，请写明不同意取消的理由')
    return
  }
  busy.value = true
  try {
    await cancelApi.rejectCancel(target.id, rejectReason.value.trim())
    ElMessage.success('已驳回取消申请，订单已恢复')
    rejectTarget.value = null
    rejectReason.value = ''
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '驳回取消失败')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="cancel-apps" v-loading="loading">
    <h1 class="page-title">取消申请处理</h1>
    <p class="muted">货主提交的取消申请在此处理。同意后订单置已取消；驳回须写明原因并恢复申请前状态。</p>

    <el-table :data="applications" size="small" empty-text="暂无取消申请">
      <el-table-column prop="application_no" label="申请号" min-width="170" />
      <el-table-column prop="order_no" label="订单号" min-width="170" />
      <el-table-column prop="mode" label="取消方式" width="120" />
      <el-table-column prop="reason" label="申请原因" min-width="180" />
      <el-table-column prop="before_status" label="申请前状态" width="120" />
      <el-table-column prop="status" label="申请状态" width="120" />
      <el-table-column prop="created_at" label="申请时间" min-width="180" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">留痕</el-button>
          <template v-if="row.status === '待公司处理'">
            <el-button link type="danger" :loading="busy" @click="agree(row)">同意</el-button>
            <el-button link @click="rejectTarget = row">驳回</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="detail" title="取消操作留痕" width="760px">
      <el-table :data="detail?.audit ?? []" size="small" empty-text="暂无取消操作记录">
        <el-table-column prop="event" label="事件" width="110" />
        <el-table-column label="操作人">
          <template #default="{ row }">{{ row.actor }} · {{ row.actor_id }}</template>
        </el-table-column>
        <el-table-column label="状态变化" min-width="200">
          <template #default="{ row }">{{ row.from_status }} → {{ row.to_status }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" min-width="180" />
        <el-table-column prop="created_at" label="时间" min-width="180" />
      </el-table>
    </el-dialog>

    <el-dialog v-model="rejectTarget" title="驳回取消申请" width="480px">
      <p class="muted">驳回后订单恢复到申请前状态，原因将通知货主并写入留痕。</p>
      <el-input
        v-model="rejectReason"
        type="textarea"
        :rows="3"
        maxlength="500"
        placeholder="请写明驳回原因"
      />
      <template #footer>
        <el-button @click="rejectTarget = null">取消</el-button>
        <el-button type="primary" :loading="busy" @click="reject">确认驳回</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.cancel-apps h1 { margin: 0 0 var(--space-2); }
.muted { margin: 0 0 var(--space-4); color: var(--color-text-muted); font-size: var(--font-size-sm); }
</style>
