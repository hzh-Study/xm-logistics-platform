<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getShipperProgress } from '@/api/checkin'
import type { TaskProgress } from '@/types/checkin'

const route = useRoute()
const orderId = Number(route.params.orderId)
const progress = ref<TaskProgress | null>(null)
const loading = ref(false)

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    progress.value = await getShipperProgress(orderId)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取运输进度失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="progress-page" v-loading="loading">
    <h1>运输进度 · {{ progress?.order_no ?? '—' }}</h1>

    <template v-if="progress">
      <el-card class="panel" shadow="never">
        <div class="headline">
          <span>运输订单状态：{{ progress.order_status }}</span>
          <span>运输任务状态：{{ progress.task_status }}</span>
          <span>任务号：{{ progress.task_no }}</span>
        </div>
        <p class="muted">计划装货 {{ progress.planned_load_at }} → 计划送达 {{ progress.planned_deliver_at }}</p>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>发货地打卡</h2>
        <el-table :data="progress.checkins" size="small" empty-text="司机尚未打卡">
          <el-table-column prop="arrived_at" label="到达时间" min-width="170" />
          <el-table-column prop="position_status" label="位置判定" width="100" />
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
        <h2>装货照片与异常</h2>
        <el-table :data="progress.loading_photos" size="small" empty-text="司机尚未上传装货照片">
          <el-table-column prop="phase" label="阶段" width="100" />
          <el-table-column prop="paths" label="照片相对路径" min-width="240">
            <template #default="scope">{{ (scope.row.paths as string[]).join('，') }}</template>
          </el-table-column>
        </el-table>
        <el-table :data="progress.loading_anomalies" size="small" empty-text="无装货异常" class="second-table">
          <el-table-column prop="kind" label="异常类型" width="110" />
          <el-table-column prop="detail" label="详情" min-width="220" />
        </el-table>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>起运确认</h2>
        <p v-if="!progress.confirmation" class="muted">尚未完成货物与车辆确认</p>
        <p v-else>
          货物核对：{{ progress.confirmation.cargo_confirmed ? '已完成' : '未完成' }} ·
          车辆核对：{{ progress.confirmation.vehicle_confirmed ? '已完成' : '未完成' }}
        </p>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>收货地打卡</h2>
        <el-table :data="progress.arrival_checkins" size="small" empty-text="司机尚未在收货地打卡">
          <el-table-column prop="arrived_at" label="到达时间" min-width="170" />
          <el-table-column prop="position_status" label="位置判定" width="100" />
          <el-table-column prop="photos" label="现场照片" min-width="180">
            <template #default="scope">{{ (scope.row.photos as string[]).join('，') }}</template>
          </el-table-column>
          <el-table-column prop="notes" label="备注" min-width="140" />
        </el-table>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>卸货记录</h2>
        <el-table :data="progress.unloading_photos" size="small" empty-text="司机尚未上传卸货照片">
          <el-table-column prop="phase" label="阶段" width="100" />
          <el-table-column prop="paths" label="照片相对路径" min-width="240">
            <template #default="scope">{{ (scope.row.paths as string[]).join('，') }}</template>
          </el-table-column>
        </el-table>
        <el-table :data="progress.unloading_anomalies" size="small" empty-text="无卸货异常" class="second-table">
          <el-table-column prop="kind" label="异常类型" width="110" />
          <el-table-column prop="detail" label="详情" min-width="220" />
        </el-table>
      </el-card>

      <el-card class="panel" shadow="never">
        <h2>签收凭证（只读）</h2>
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
        </template>
        <p v-if="progress.signoff_confirmation" class="confirmed">
          物流公司已依据凭证确认完成 · {{ progress.signoff_confirmation.created_at }}
        </p>
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
.second-table { margin-top: var(--space-4); }
.confirmed { margin: var(--space-3) 0 0; font-size: var(--font-size-sm); color: var(--color-success); }
</style>
