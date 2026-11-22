<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import type { TransportTask, TaskStatus } from '@/types/dispatch'

const rows = ref<TransportTask[]>([])
const loading = ref(false)
const detail = ref<TransportTask | null>(null)
const filter = reactive({
  status: '' as TaskStatus | '',
  order_id: undefined as number | undefined,
  task_no: '',
})

const statuses: TaskStatus[] = [
  '待司机确认',
  '待装货',
  '运输中',
  '待签收',
  '待确认完成',
  '已完成',
  '异常',
  '已拒绝',
]

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await adminApi.fetchPlatformTasks({ ...filter })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载任务失败')
  } finally {
    loading.value = false
  }
}

async function openDetail(task: TransportTask): Promise<void> {
  try {
    detail.value = await adminApi.fetchPlatformTask(task.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取任务详情失败')
  }
}

onMounted(load)
</script>

<template>
  <section class="tasks">
    <h1 class="page-title">全平台运输任务</h1>

    <div class="toolbar">
      <el-input v-model="filter.task_no" class="field" placeholder="任务编号" clearable />
      <el-select v-model="filter.status" class="field" placeholder="全部状态" clearable>
        <el-option v-for="status in statuses" :key="status" :label="status" :value="status" />
      </el-select>
      <el-input-number
        v-model="filter.order_id"
        class="field"
        :min="1"
        controls-position="right"
        placeholder="订单 id"
      />
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="task_no" label="任务编号" width="180" />
      <el-table-column prop="order_no" label="所属订单" width="180" />
      <el-table-column prop="driver_name" label="执行司机" />
      <el-table-column prop="vehicle_plate" label="执行车辆" />
      <el-table-column label="状态">
        <template #default="{ row }">
          <el-tag :type="row.status === '已完成' ? 'success' : 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="planned_load_at" label="计划装货" width="200" />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button type="primary" link @click="openDetail(row)">详情</el-button>
        </template>
      </el-table-column>
      <template #empty><span>暂无符合条件的运输任务。</span></template>
    </el-table>

    <el-dialog v-model="detail" title="运输任务详情" width="680px">
      <template v-if="detail">
        <p class="detail-row">任务编号：{{ detail.task_no }} · 状态：{{ detail.status }}</p>
        <p class="detail-row">所属订单：{{ detail.order_no }}（id {{ detail.order_id }}）</p>
        <p class="detail-row">司机：{{ detail.driver_name }} · {{ detail.driver_phone }}</p>
        <p class="detail-row">车辆：{{ detail.vehicle_plate }} · 公司账号 {{ detail.carrier_id }}</p>
        <p class="detail-row">计划装货：{{ detail.planned_load_at }}</p>
        <p class="detail-row">计划送达：{{ detail.planned_deliver_at }}</p>
        <p class="detail-row">注意事项：{{ detail.notes || '无' }}</p>
        <p class="detail-row">司机拒绝原因：{{ detail.reject_reason || '无' }}</p>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.tasks {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0 0 var(--space-6);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.field {
  width: 180px;
}

.detail-row {
  margin: 0 0 var(--space-2);
  color: var(--color-text-muted);
}
</style>
