<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import { listDrivers } from '@/api/driver'
import { assignVehicle, createVehicle, listVehicles, setVehicleAvailability, setVehicleDocumentStatus, setVehicleLifecycle } from '@/api/vehicle'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { Driver } from '@/types/driver'
import type { Availability, DocumentStatus, Lifecycle, OwnerType, Vehicle, VehicleCreatePayload } from '@/types/vehicle'

const vehicles = ref<Vehicle[]>([])
const drivers = ref<Driver[]>([])
const loading = ref(false)
const saving = ref(false)
const filter = reactive<{ plate?: string; availability?: Availability; lifecycle?: Lifecycle; owner_type?: OwnerType }>({})

const createOpen = ref(false)
const assignOpen = ref(false)
const statusOpen = ref(false)
const assigning = ref<Vehicle | null>(null)
const statusTarget = ref<Vehicle | null>(null)

const createForm = reactive<VehicleCreatePayload>({
  plate_no: '', vehicle_type: '厢式货车', length_m: 4.2, max_load_kg: 5000,
  owner_type: '公司', owner_driver_id: null, document_status: '待审核',
})
const assignForm = reactive({ driver_account_id: null as number | null })
const statusForm = reactive({
  availability: '可用' as Availability,
  lifecycle: '在册' as Lifecycle,
  document_status: '待审核' as DocumentStatus,
})

const VEHICLE_TYPE_OPTIONS = [
  { label: '平板车', value: '平板货车' },
  { label: '厢式货车', value: '厢式货车' },
  { label: '高栏车', value: '高栏货车' },
  { label: '自卸车', value: '其他' },
  { label: '冷藏车', value: '冷藏车' },
]

function displayVehicleType(value: string): string {
  const found = VEHICLE_TYPE_OPTIONS.find((item) => item.value === value)
  return found?.label ?? value
}

const filtered = () => vehicles.value.filter((vehicle) =>
  (!filter.plate || vehicle.plate_no.includes(filter.plate)) &&
  (!filter.availability || vehicle.availability === filter.availability) &&
  (!filter.lifecycle || vehicle.lifecycle === filter.lifecycle) &&
  (!filter.owner_type || vehicle.owner_type === filter.owner_type),
)

async function load(): Promise<void> {
  loading.value = true
  try {
    const [vehicleRows, driverRows] = await Promise.all([listVehicles(), listDrivers()])
    vehicles.value = vehicleRows
    drivers.value = driverRows
  } catch (error) {
    report(error, '读取车辆列表失败')
  } finally {
    loading.value = false
  }
}

function reset(): void {
  filter.plate = ''
  filter.availability = undefined
  filter.lifecycle = undefined
  filter.owner_type = undefined
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
    plate_no: '', vehicle_type: '厢式货车', length_m: 4.2, max_load_kg: 5000,
    owner_type: '公司', owner_driver_id: null, document_status: '待审核',
  })
  createOpen.value = true
}

async function submitCreate(): Promise<void> {
  if (!createForm.plate_no.trim()) {
    ElMessage.warning('请填写车牌号')
    return
  }
  saving.value = true
  try {
    await createVehicle({ ...createForm })
    ElMessage.success('车辆已登记并纳入本公司管理')
    createOpen.value = false
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
  assignOpen.value = true
}

async function submitAssign(): Promise<void> {
  const target = assigning.value
  if (!target || assignForm.driver_account_id === null) return
  saving.value = true
  try {
    await assignVehicle(target.id, assignForm.driver_account_id)
    ElMessage.success('车辆已分配给司机')
    assignOpen.value = false
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
  statusOpen.value = true
}

async function submitStatus(): Promise<void> {
  const target = statusTarget.value
  if (!target) return
  saving.value = true
  try {
    if (statusForm.availability !== target.availability) await setVehicleAvailability(target.id, statusForm.availability)
    if (statusForm.lifecycle !== target.lifecycle) await setVehicleLifecycle(target.id, statusForm.lifecycle)
    if (statusForm.document_status !== target.document_status) await setVehicleDocumentStatus(target.id, statusForm.document_status)
    ElMessage.success('车辆状态已更新')
    statusOpen.value = false
    await load()
  } catch (error) {
    report(error, '更新车辆状态失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="车辆管理" :subtitle="`在册车辆 ${vehicles.filter((v) => v.lifecycle === '在册').length} 台 · 可用 ${vehicles.filter((v) => v.availability === '可用').length} / 占用 ${vehicles.filter((v) => v.availability === '占用中').length} / 暂停使用 ${vehicles.filter((v) => v.availability === '暂停使用').length}`">
      <template #actions><el-button type="primary" @click="openCreate">登记车辆</el-button></template>
    </PageHeader>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="vh-plate">车牌号</label><el-input id="vh-plate" v-model="filter.plate" placeholder="请输入车牌号" clearable /></div>
        <div class="field">
          <label class="field__label" for="vh-avail">可用性</label>
          <el-select id="vh-avail" v-model="filter.availability" placeholder="全部" clearable>
            <el-option v-for="item in ['可用', '占用中', '暂停使用']" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="vh-life">生命周期</label>
          <el-select id="vh-life" v-model="filter.lifecycle" placeholder="全部" clearable>
            <el-option v-for="item in ['在册', '维修中', '已停用']" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="vh-owner">归属</label>
          <el-select id="vh-owner" v-model="filter.owner_type" placeholder="全部" clearable>
            <el-option label="公司自有" value="公司" /><el-option label="司机自带" value="司机" />
          </el-select>
        </div>
      </div>
      <div class="filter-actions">
        <el-button @click="reset">重置</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">车辆列表</span><span class="panel-hint">可用性与生命周期为两个独立维度；维修中或已停用车辆不可派单</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!filtered().length" text="暂无车辆，点击「登记车辆」添加。" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">车牌号</th><th>类型 / 车长</th><th class="num">最大载重</th><th>归属 / 实际车主</th><th>当前司机</th><th>可用性</th><th>生命周期</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in filtered()" :key="row.id">
                <td class="num">{{ row.plate_no }}</td>
                <td>{{ displayVehicleType(row.vehicle_type) }} / {{ row.length_m }} 米</td>
                <td class="num">{{ row.max_load_kg / 1000 }} 吨</td>
                <td>{{ row.owner_type === '公司' ? '公司自有' : `司机自带 / ${row.actual_owner}` }}</td>
                <td>{{ row.current_driver || '—' }}</td>
                <td><StatusPill :text="row.availability" /></td>
                <td><StatusPill :text="row.lifecycle" /></td>
                <td class="ops">
                  <el-button type="primary" link @click="openStatus(row)">编辑</el-button>
                  <el-button type="primary" link @click="openAssign(row)">分配司机</el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ filtered().length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="createOpen" title="登记车辆">
      <template #body>
        <NoticeBar tone="warning">车辆转籍由平台管理员执行，且仅限无进行中任务的车辆。</NoticeBar>
        <form class="drawer-form">
          <div class="field"><label class="field__label"><span class="field__req">*</span>车牌号</label><el-input v-model="createForm.plate_no" /></div>
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>车辆类型</label>
            <el-select v-model="createForm.vehicle_type" style="width: 100%">
              <el-option v-for="item in VEHICLE_TYPE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </div>
          <div class="field"><label class="field__label">车长（米）</label><el-input-number v-model="createForm.length_m" :min="1" :step="0.1" style="width: 100%" /></div>
          <div class="field"><label class="field__label">最大载重（kg）</label><el-input-number v-model="createForm.max_load_kg" :min="1" :step="500" style="width: 100%" /></div>
          <div class="field">
            <label class="field__label">归属</label>
            <el-radio-group v-model="createForm.owner_type">
              <el-radio value="公司">公司自有</el-radio><el-radio value="司机">司机自带</el-radio>
            </el-radio-group>
          </div>
          <div v-if="createForm.owner_type === '司机'" class="field">
            <label class="field__label">实际车主</label>
            <el-select v-model="createForm.owner_driver_id" placeholder="全部" style="width: 100%">
              <el-option v-for="driver in drivers" :key="driver.account_id" :label="driver.name" :value="driver.account_id" />
            </el-select>
          </div>
        </form>
      </template>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">保存</el-button>
      </template>
    </DetailDrawer>

    <DetailDrawer v-model="assignOpen" title="分配司机">
      <template #body>
        <div class="field">
          <label class="field__label">司机</label>
          <el-select v-model="assignForm.driver_account_id" placeholder="全部" style="width: 100%">
            <el-option v-for="driver in drivers" :key="driver.account_id" :label="`${driver.name} · ${driver.availability} · ${driver.employment}`" :value="driver.account_id" />
          </el-select>
        </div>
      </template>
      <template #footer>
        <el-button @click="assignOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAssign">确认分配</el-button>
      </template>
    </DetailDrawer>

    <DetailDrawer v-model="statusOpen" :title="`车辆状态 · ${statusTarget?.plate_no ?? ''}`">
      <template #body>
        <form class="drawer-form">
          <div class="field"><label class="field__label">可用性</label>
            <el-select v-model="statusForm.availability" style="width: 100%">
              <el-option v-for="item in ['可用', '占用中', '暂停使用']" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field"><label class="field__label">生命周期</label>
            <el-select v-model="statusForm.lifecycle" style="width: 100%">
              <el-option v-for="item in ['在册', '维修中', '已停用']" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field"><label class="field__label">证件状态</label>
            <el-select v-model="statusForm.document_status" style="width: 100%">
              <el-option v-for="item in ['待审核', '有效', '已过期']" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
        </form>
      </template>
      <template #footer>
        <el-button @click="statusOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitStatus">保存</el-button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.drawer-form { padding-top: var(--space-4); }
</style>
