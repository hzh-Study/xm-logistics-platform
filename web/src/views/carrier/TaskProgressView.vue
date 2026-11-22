<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCarrierProgress } from '@/api/checkin'
import { confirmSignoff } from '@/api/signoff'
import type { TaskProgress } from '@/types/checkin'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.params.taskId)
const progress = ref<TaskProgress | null>(null)
const loading = ref(false)
const confirming = ref(false)

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    progress.value = await getCarrierProgress(taskId)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取运输进度失败')
  } finally {
    loading.value = false
  }
}

async function onConfirm(): Promise<void> {
  if (!progress.value?.signoff_voucher) {
    ElMessage.warning('司机尚未提交签收凭证')
    return
  }
  try {
    await ElMessageBox.confirm('依据司机提交的签收凭证确认任务完成？', '确认完成', {
      type: 'warning',
    })
  } catch {
    return
  }
  confirming.value = true
  try {
    progress.value = await confirmSignoff(taskId, { confirmed: true, notes: '凭证齐全，确认完成' })
    ElMessage.success('已确认完成，运输任务与运输订单均已完成')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '确认失败')
  } finally {
    confirming.value = false
  }
}
</script>

<template>
  <div class="progress-page" v-loading="loading">
    <h1>运输进度 · {{ progress?.task_no ?? '—' }}</h1>

    <template v-if="progress">
      <el-card class="panel" shadow="never">
        <div class="headline">
          <span>运输任务状态：{{ progress.task_status }}</span>
          <span>运输订单状态：{{ progress.order_status }}</span>
          <span>订单号：{{ progress.order_no }}</span>
        </div>
        <p class="muted">计划装货 {{ progress.planned_load_at }} → 计划送达 {{ progress.planned_deliver_at }}</p>
        <el-button link type="primary" @click="router.push(`/carrier/tasks/${taskId}/exceptions`)">
          查看并处理在途异常
        </el-button>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>发货地打卡</h2>
        <el-table :data="progress.checkins" size="small" empty-text="司机尚未打卡">
          <el-table-column prop="arrived_at" label="到达时间" min-width="170" />
          <el-table-column prop="position_status" label="位置判定" width="100" />
          <el-table-column prop="distance_m" label="距离（米）" width="100" />
          <el-table-column prop="photos" label="现场照片" min-width="180">
            <template #default="scope">{{ (scope.row.photos as string[]).join('，') }}</template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="140" />
        </el-table>
        <el-alert
          v-for="note in progress.exception_notes"
          :key="note.id"
          class="notice"
          type="warning"
          :closable="false"
          :title="`位置异常说明：${note.note}`"
        />
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>装货照片</h2>
        <el-table :data="progress.loading_photos" size="small" empty-text="司机尚未上传装货照片">
          <el-table-column prop="phase" label="阶段" width="100" />
          <el-table-column prop="paths" label="照片相对路径" min-width="260">
            <template #default="scope">{{ (scope.row.paths as string[]).join('，') }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="上传时间" min-width="170" />
        </el-table>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>装货异常</h2>
        <el-table :data="progress.loading_anomalies" size="small" empty-text="无装货异常">
          <el-table-column prop="kind" label="异常类型" width="110" />
          <el-table-column prop="detail" label="详情" min-width="220" />
          <el-table-column prop="photos" label="凭证" min-width="180">
            <template #default="scope">{{ (scope.row.photos as string[]).join('，') || '—' }}</template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>起运确认</h2>
        <p v-if="!progress.confirmation" class="muted">尚未完成货物与车辆确认</p>
        <p v-else>
          货物核对：{{ progress.confirmation.cargo_confirmed ? '已完成' : '未完成' }} ·
          车辆核对：{{ progress.confirmation.vehicle_confirmed ? '已完成' : '未完成' }} ·
          备注：{{ progress.confirmation.notes || '—' }}
        </p>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>收货地打卡</h2>
        <el-table :data="progress.arrival_checkins" size="small" empty-text="司机尚未在收货地打卡">
          <el-table-column prop="arrived_at" label="到达时间" min-width="170" />
          <el-table-column prop="position_status" label="位置判定" width="100" />
          <el-table-column prop="distance_m" label="距离（米）" width="100" />
          <el-table-column prop="photos" label="现场照片" min-width="180">
            <template #default="scope">{{ (scope.row.photos as string[]).join('，') }}</template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="140" />
        </el-table>
        <el-alert
          v-for="note in progress.arrival_notes"
          :key="note.id"
          class="notice"
          type="warning"
          :closable="false"
          :title="`位置异常说明：${note.note}`"
        />
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>卸货照片与异常</h2>
        <el-table :data="progress.unloading_photos" size="small" empty-text="司机尚未上传卸货照片">
          <el-table-column prop="phase" label="阶段" width="100" />
          <el-table-column prop="paths" label="照片相对路径" min-width="260">
            <template #default="scope">{{ (scope.row.paths as string[]).join('，') }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="上传时间" min-width="170" />
        </el-table>
        <el-table :data="progress.unloading_anomalies" size="small" empty-text="无卸货异常" class="sub-table">
          <el-table-column prop="kind" label="异常类型" width="110" />
          <el-table-column prop="detail" label="详情" min-width="220" />
          <el-table-column prop="photos" label="凭证" min-width="180">
            <template #default="scope">{{ (scope.row.photos as string[]).join('，') || '—' }}</template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>签收凭证</h2>
        <p v-if="!progress.signoff_voucher" class="muted">司机尚未提交签收资料</p>
        <template v-else>
          <div class="headline">
            <span>凭证号：{{ progress.signoff_voucher.voucher_no }}</span>
            <span>收货情况：{{ progress.signoff_voucher.receiving_condition }}</span>
            <span>收货时间：{{ progress.signoff_voucher.received_at }}</span>
            <span>收货人：{{ progress.signoff_voucher.receiver_name }}</span>
          </div>
          <p class="muted">
            签收照片：{{ progress.signoff_voucher.signature_photos.join('，') }} ·
            凭证：{{ progress.signoff_voucher.vouchers.join('，') }}
          </p>
          <p v-if="progress.signoff_voucher.notes" class="muted">备注：{{ progress.signoff_voucher.notes }}</p>
        </template>
        <p v-if="progress.signoff_confirmation" class="confirmed">
          已确认完成 · 确认记录 {{ progress.signoff_confirmation.id }} · {{ progress.signoff_confirmation.notes }}
        </p>
        <el-button
          v-if="progress.task_status === '待确认完成' && progress.signoff_voucher"
          class="confirm-btn"
          type="primary"
          :loading="confirming"
          @click="onConfirm"
        >
          依据签收凭证确认完成
        </el-button>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.progress-page h1 { margin: 0 0 var(--space-4); font-size: var(--font-size-xl); }
.panel { margin-bottom: var(--space-4); }
.panel h2 { margin: 0 0 var(--space-3); font-size: var(--font-size-md); }
.headline { display: flex; flex-wrap: wrap; gap: var(--space-4); font-size: var(--font-size-sm); }
.muted { margin: var(--space-2) 0 0; color: var(--color-text-muted); font-size: var(--font-size-sm); }
.notice { margin-top: var(--space-2); }
.sub-table { margin-top: var(--space-3); }
.confirmed { margin: var(--space-3) 0 0; font-size: var(--font-size-sm); color: var(--color-success); }
.confirm-btn { margin-top: var(--space-4); }
</style>
