<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import { listDrivers } from '@/api/driver'
import {
  assignVehicle,
  createVehicle,
  listVehicles,
  setVehicleAvailability,
  setVehicleDocumentStatus,
  setVehicleLifecycle,
} from '@/api/vehicle'
import type { Driver } from '@/types/driver'
import type {
  Availability,
  DocumentStatus,
  Lifecycle,
  OwnerType,
  Vehicle,
  VehicleCreatePayload,
  VehicleType,
} from '@/types/vehicle'

const vehicles = ref<Vehicle[]>([])
const drivers = ref<Driver[]>([])
const loading = ref(false)
const saving = ref(false)
const filter = reactive<{
  availability?: Availability
  lifecycle?: Lifecycle
  owner_type?: OwnerType
  assignable: boolean
}>({ assignable: false })

const createVisible = ref(false)
const assignVisible = ref(false)
const statusVisible = ref(false)
const assigning = ref<Vehicle | null>(null)
const statusTarget = ref<Vehicle | null>(null)

const createForm = reactive<VehicleCreatePayload>({
  plate_no: '',
  vehicle_type: '厢式货车',
  length_m: 4.2,
  max_load_kg: 5000,
  owner_type: '公司',
  owner_driver_id: null,
  document_status: '待审核',
})
const assignForm = reactive({ driver_account_id: null as number | null })
const statusForm = reactive({
  availability: '可用' as Availability,
  lifecycle: '在册' as Lifecycle,
  document_status: '待审核' as DocumentStatus,
})

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    const [vehicleRows, driverRows] = await Promise.all([
      listVehicles({
        availability: filter.availability,
        lifecycle: filter.lifecycle,
        owner_type: filter.owner_type,
        assignable: filter.assignable,
      }),
      listDrivers(),
    ])
    vehicles.value = vehicleRows
    drivers.value = driverRows
  } catch (error) {
    report(error, '读取车辆列表失败')
  } finally {
    loading.value = false
  }
}

function report(error: unknown, fallback: string): void {
  if (error instanceof ApiError && Array.isArray(error.details)) {
    const first = error.details[0] as { field?: string; message?: string }
    ElMessage.error(`${first.field ?? '字段'}：${first.message ?? fallback}`)
    return
  }
  ElMessage.error(error instanceof Error ? error.message : fallback)
}

function openCreate(): void {
  Object.assign(createForm, {
    plate_no: '',
    vehicle_type: '厢式货车',
    length_m: 4.2,
    max_load_kg: 5000,
    owner_type: '公司',
    owner_driver_id: null,
    document_status: '待审核',
  })
  createVisible.value = true
}

function onOwnerTypeChange(): void {
  if (createForm.owner_type === '公司') createForm.owner_driver_id = null
}

async function submitCreate(): Promise<void> {
  saving.value = true
  try {
    await createVehicle({ ...createForm })
    ElMessage.success('车辆已登记并纳入本公司管理')
    createVisible.value = false
    await load()
  } catch (error) {
    report(error, '登记车辆失败')
  } finally {
    saving.value = false
  }
}

function openAssign(row: Vehicle): void {
  assigning.value = row
  assignForm.driver_account_id = row.current_driver_id ?? null
  assignVisible.value = true
}

async function submitAssign(): Promise<void> {
  const target = assigning.value
  if (!target || assignForm.driver_account_id === null) return
  saving.value = true
  try {
    await assignVehicle(target.id, assignForm.driver_account_id)
    ElMessage.success('车辆已分配给司机')
    assignVisible.value = false
    await load()
  } catch (error) {
    report(error, '分配车辆失败')
  } finally {
    saving.value = false
  }
}

function openStatus(row: Vehicle): void {
  statusTarget.value = row
  statusForm.availability = row.availability
  statusForm.lifecycle = row.lifecycle
  statusForm.document_status = row.document_status
  statusVisible.value = true
}

async function submitStatus(): Promise<void> {
  const target = statusTarget.value
  if (!target) return
  saving.value = true
  try {
    if (statusForm.availability !== target.availability) {
      await setVehicleAvailability(target.id, statusForm.availability)
    }
    if (statusForm.lifecycle !== target.lifecycle) {
      await setVehicleLifecycle(target.id, statusForm.lifecycle)
    }
    if (statusForm.document_status !== target.document_status) {
      await setVehicleDocumentStatus(target.id, statusForm.document_status)
    }
    ElMessage.success('车辆状态已更新')
    statusVisible.value = false
    await load()
  } catch (error) {
    report(error, '更新车辆状态失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="vehicles">
    <div class="header-row">
      <div>
        <h1 class="page-title">车辆管理</h1>
        <p class="page-note">公司车辆与司机个人车辆统一在册；可用性与生命周期为两个独立维度。</p>
      </div>
      <el-button type="primary" @click="openCreate">登记车辆</el-button>
    </div>

    <div class="filter-row">
      <el-select v-model="filter.availability" placeholder="可用性" clearable class="filter">
        <el-option v-for="item in ['可用', '占用中', '暂停使用']" :key="item" :value="item" />
      </el-select>
      <el-select v-model="filter.lifecycle" placeholder="生命周期" clearable class="filter">
        <el-option v-for="item in ['在册', '维修中', '已停用']" :key="item" :value="item" />
      </el-select>
      <el-select v-model="filter.owner_type" placeholder="实际所有者" clearable class="filter">
        <el-option v-for="item in ['公司', '司机']" :key="item" :value="item" />
      </el-select>
      <el-checkbox v-model="filter.assignable">仅看可分配</el-checkbox>
      <el-button @click="load">筛选</el-button>
    </div>

    <el-table :data="vehicles" border v-loading="loading" class="table">
      <el-table-column prop="plate_no" label="车牌" width="110" />
      <el-table-column prop="vehicle_type" label="类型" width="100" />
      <el-table-column prop="length_m" label="长度(米)" width="100" />
      <el-table-column prop="max_load_kg" label="最大载重(千克)" width="130" />
      <el-table-column prop="actual_owner" label="实际所有者" width="110" />
      <el-table-column prop="current_driver" label="当前司机" width="110">
        <template #default="{ row }: { row: Vehicle }">{{ row.current_driver || '—' }}</template>
      </el-table-column>
      <el-table-column prop="availability" label="可用性" width="100" />
      <el-table-column prop="lifecycle" label="生命周期" width="100" />
      <el-table-column prop="document_status" label="证件状态" width="100" />
      <el-table-column label="可分配" width="90">
        <template #default="{ row }: { row: Vehicle }">
          <el-tag :type="row.assignable ? 'success' : 'info'" size="small">
            {{ row.assignable ? '可分配' : '不可分配' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="180">
        <template #default="{ row }: { row: Vehicle }">
          <el-button
            link
            type="primary"
            :disabled="!row.assignable || row.owner_type !== '公司'"
            @click="openAssign(row)"
          >分配</el-button>
          <el-button link type="primary" @click="openStatus(row)">状态</el-button>
        </template>
      </el-table-column>
      <template #empty>暂无车辆，点击「登记车辆」为本公司在册。</template>
    </el-table>

    <el-dialog v-model="createVisible" title="登记车辆" width="560px">
      <el-form :model="createForm" label-width="110px">
        <el-form-item label="车牌" required>
          <el-input v-model="createForm.plate_no" maxlength="32" />
        </el-form-item>
        <el-form-item label="车辆类型" required>
          <el-select v-model="createForm.vehicle_type">
            <el-option v-for="item in ['厢式货车', '平板货车', '高栏货车', '冷藏车', '其他']" :key="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="车长(米)" required>
          <el-input-number v-model="createForm.length_m" :min="0.1" :max="30" :step="0.1" :precision="2" />
        </el-form-item>
        <el-form-item label="最大载重(千克)" required>
          <el-input-number v-model="createForm.max_load_kg" :min="1" :max="100000" :step="100" />
        </el-form-item>
        <el-form-item label="实际所有者" required>
          <el-select v-model="createForm.owner_type" @change="onOwnerTypeChange">
            <el-option label="公司车辆" value="公司" />
            <el-option label="司机个人车辆" value="司机" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="createForm.owner_type === '司机'" label="所属司机" required>
          <el-select v-model="createForm.owner_driver_id" placeholder="选择本公司司机">
            <el-option v-for="driver in drivers" :key="driver.account_id" :label="`${driver.name}（${driver.phone}）`" :value="driver.account_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="证件状态">
          <el-select v-model="createForm.document_status">
            <el-option v-for="item in ['待审核', '有效', '已过期']" :key="item" :value="item" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">登记</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="assignVisible" title="分配车辆" width="480px">
      <p class="dialog-note">仅公司名下、可用且在册的车辆可分配；个人车辆默认关联所属司机。</p>
      <el-form label-width="100px">
        <el-form-item label="司机">
          <el-select v-model="assignForm.driver_account_id" placeholder="选择本公司司机">
            <el-option v-for="driver in drivers" :key="driver.account_id" :label="`${driver.name}（${driver.phone}）`" :value="driver.account_id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAssign">分配</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="statusVisible" title="设置车辆状态" width="480px">
      <p class="dialog-note">可用性与生命周期相互独立；维修中、已停用或暂停使用的车辆不可派新任务。</p>
      <el-form label-width="100px">
        <el-form-item label="可用性">
          <el-select v-model="statusForm.availability">
            <el-option v-for="item in ['可用', '占用中', '暂停使用']" :key="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="生命周期">
          <el-select v-model="statusForm.lifecycle">
            <el-option v-for="item in ['在册', '维修中', '已停用']" :key="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="证件状态">
          <el-select v-model="statusForm.document_status">
            <el-option v-for="item in ['待审核', '有效', '已过期']" :key="item" :value="item" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitStatus">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.vehicles {
  padding: var(--space-2) 0;
}

.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
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

.filter-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.filter {
  width: 150px;
}

.table {
  width: 100%;
}

.dialog-note {
  margin: 0 0 var(--space-4);
  color: var(--color-text-muted);
}
</style>
