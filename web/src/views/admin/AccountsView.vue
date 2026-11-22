<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import type { DriverSummary, ShipperSummary, VehicleSummary } from '@/types/admin'

type Tab = '货主' | '司机' | '车辆'
const tab = ref<Tab>('货主')
const loading = ref(false)
const keyword = ref('')
const shippers = ref<ShipperSummary[]>([])
const drivers = ref<DriverSummary[]>([])
const vehicles = ref<VehicleSummary[]>([])

async function load(): Promise<void> {
  loading.value = true
  try {
    if (tab.value === '货主') {
      shippers.value = await adminApi.fetchShippers({ company_name: keyword.value })
    } else if (tab.value === '司机') {
      drivers.value = await adminApi.fetchDrivers({ driver_name: keyword.value })
    } else {
      vehicles.value = await adminApi.fetchVehicles({ plate_no: keyword.value })
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载账号数据失败')
  } finally {
    loading.value = false
  }
}

function switchTab(next: Tab): void {
  tab.value = next
  keyword.value = ''
  load()
}

onMounted(load)
</script>

<template>
  <section class="accounts">
    <div class="toolbar">
      <h1 class="page-title">全平台主体查询</h1>
      <el-radio-group :model-value="tab" @update:model-value="switchTab">
        <el-radio-button value="货主">货主</el-radio-button>
        <el-radio-button value="司机">司机</el-radio-button>
        <el-radio-button value="车辆">车辆</el-radio-button>
      </el-radio-group>
      <el-input v-model="keyword" class="field" :placeholder="tab === '车辆' ? '车牌号' : '名称'" clearable />
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table v-if="tab === '货主'" :data="shippers" v-loading="loading" row-key="account_id">
      <el-table-column prop="account_id" label="账号 id" width="90" />
      <el-table-column prop="company_name" label="货主名称" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="profile_type" label="认证类型" width="100" />
      <el-table-column prop="auth_status" label="认证状态" width="110" />
      <el-table-column prop="account_status" label="账号状态" width="110" />
      <template #empty><span>暂无符合条件的货主。</span></template>
    </el-table>

    <el-table v-else-if="tab === '司机'" :data="drivers" v-loading="loading" row-key="account_id">
      <el-table-column prop="account_id" label="账号 id" width="90" />
      <el-table-column prop="driver_name" label="司机姓名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="license_no" label="驾驶证号" />
      <el-table-column prop="carrier_id" label="所属公司 id" width="110" />
      <el-table-column prop="auth_status" label="认证状态" width="110" />
      <el-table-column prop="account_status" label="账号状态" width="110" />
      <template #empty><span>暂无符合条件的司机。</span></template>
    </el-table>

    <el-table v-else :data="vehicles" v-loading="loading" row-key="id">
      <el-table-column prop="id" label="车辆 id" width="90" />
      <el-table-column prop="plate_no" label="车牌号" />
      <el-table-column prop="carrier_id" label="所属公司 id" width="110" />
      <el-table-column prop="vehicle_type" label="车辆类型" />
      <el-table-column prop="availability" label="可用性" width="100" />
      <el-table-column prop="lifecycle" label="生命周期" width="100" />
      <el-table-column prop="document_review_status" label="证件审核" width="110" />
      <template #empty><span>暂无符合条件的车辆。</span></template>
    </el-table>
  </section>
</template>

<style scoped>
.accounts {
  padding: var(--space-2) 0;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.page-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.field {
  width: 200px;
}
</style>
