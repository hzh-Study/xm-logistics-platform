<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import type { VehicleTransfer } from '@/types/admin'

const rows = ref<VehicleTransfer[]>([])
const loading = ref(false)
const form = reactive({ vehicle_id: undefined as number | undefined, to_carrier_id: undefined as number | undefined, reason: '' })
const filter = reactive({ vehicle_id: undefined as number | undefined })

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await adminApi.fetchVehicleTransfers(filter.vehicle_id)
  } catch (error) {
    ElMessage.error(errorText(error, '加载转籍历史失败'))
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  if (!form.vehicle_id || !form.to_carrier_id || !form.reason.trim()) {
    ElMessage.warning('车辆、转入物流公司账号与转籍原因必填')
    return
  }
  try {
    const result = await adminApi.transferVehicle({
      vehicle_id: form.vehicle_id,
      to_carrier_id: form.to_carrier_id,
      reason: form.reason,
    })
    ElMessage.success(`车辆 ${result.plate_no} 已完成转籍`)
    form.reason = ''
    await load()
  } catch (error) {
    ElMessage.error(errorText(error, '车辆转籍失败'))
  }
}

onMounted(load)
</script>

<template>
  <section class="vehicle-transfers">
    <h1 class="page-title">车辆转籍</h1>
    <p class="page-note">仅当车辆无进行中运输任务时可转籍；保留转籍前后归属，历史任务车辆信息不改写。</p>

    <div class="panel">
      <el-form label-position="top" class="form">
        <el-form-item label="车辆 id">
          <el-input-number v-model="form.vehicle_id" :min="1" controls-position="right" placeholder="车辆 id" />
        </el-form-item>
        <el-form-item label="转入物流公司账号 id">
          <el-input-number v-model="form.to_carrier_id" :min="1" controls-position="right" placeholder="账号 id" />
        </el-form-item>
        <el-form-item label="转籍原因">
          <el-input v-model="form.reason" type="textarea" :rows="2" maxlength="1000" placeholder="写明转籍原因" />
        </el-form-item>
        <el-button type="primary" @click="submit">执行转籍</el-button>
      </el-form>
    </div>

    <h2 class="section-title">转籍历史</h2>
    <div class="toolbar">
      <el-input-number
        v-model="filter.vehicle_id"
        :min="1"
        controls-position="right"
        placeholder="按车辆 id 筛选"
      />
      <el-button @click="load">查询</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="transfer_no" label="转籍编号" width="170" />
      <el-table-column prop="plate_no" label="车牌号" width="120" />
      <el-table-column prop="vehicle_id" label="车辆 id" width="100" />
      <el-table-column label="转出归属" width="130">
        <template #default="{ row }"><el-tag type="info">公司 {{ row.before_carrier_id }}</el-tag></template>
      </el-table-column>
      <el-table-column label="转入归属" width="130">
        <template #default="{ row }"><el-tag type="success">公司 {{ row.after_carrier_id }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="reason" label="转籍原因" show-overflow-tooltip />
      <el-table-column prop="created_at" label="转籍时间" width="200" />
      <template #empty><span>暂无转籍记录。</span></template>
    </el-table>
  </section>
</template>

<style scoped>
.vehicle-transfers {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0 0 var(--space-1);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.page-note {
  margin: 0 0 var(--space-6);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.panel {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.form {
  max-width: 520px;
}

.section-title {
  margin: var(--space-6) 0 var(--space-3);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
</style>
