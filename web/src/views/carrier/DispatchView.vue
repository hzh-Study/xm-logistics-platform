<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import {
  createTask,
  dispatchHistory,
  listCarrierOrders,
  listTasks,
  redispatchTask,
} from '@/api/dispatch'
import { listDrivers } from '@/api/driver'
import { listVehicles } from '@/api/vehicle'
import type { Driver } from '@/types/driver'
import type { Order } from '@/types/order'
import type { Vehicle } from '@/types/vehicle'
import type { DispatchHistory, TaskStatus, TransportTask } from '@/types/dispatch'

const orders = ref<Order[]>([])
const tasks = ref<TransportTask[]>([])
const drivers = ref<Driver[]>([])
const vehicles = ref<Vehicle[]>([])
const loading = ref(false)
const saving = ref(false)
const createVisible = ref(false)
const redispatchVisible = ref(false)
const historyVisible = ref(false)
const historyRows = ref<DispatchHistory[]>([])
const targetTask = ref<TransportTask | null>(null)

const form = reactive({
  order_id: null as number | null,
  driver_account_id: null as number | null,
  vehicle_id: null as number | null,
  planned_load_at: '',
  planned_deliver_at: '',
  notes: '',
})
const redispatchForm = reactive({
  driver_account_id: null as number | null,
  vehicle_id: null as number | null,
  reason: '',
})

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    const [orderRows, taskRows, driverRows, vehicleRows] = await Promise.all([
      listCarrierOrders(),
      listTasks(),
      listDrivers(),
      listVehicles({ assignable: true }),
    ])
    orders.value = orderRows.filter((row) => row.status === '已承接')
    tasks.value = taskRows
    drivers.value = driverRows.filter((row) => row.can_dispatch_new)
    vehicles.value = vehicleRows
  } catch (error) {
    report(error, '读取派单数据失败')
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

/** datetime-local 的值补全秒与本地时区偏移，满足服务端 ISO 8601 约束。 */
function toIso(value: string): string {
  if (!value) return ''
  return value.length === 16 ? `${value}:00+00:00` : value
}

function openCreate(order?: Order): void {
  Object.assign(form, {
    order_id: order?.id ?? null,
    driver_account_id: null,
    vehicle_id: null,
    planned_load_at: '',
    planned_deliver_at: '',
    notes: '',
  })
  createVisible.value = true
}

async function submitCreate(): Promise<void> {
  if (
    form.order_id === null ||
    form.driver_account_id === null ||
    form.vehicle_id === null
  ) {
    ElMessage.warning('请选择订单、司机与车辆')
    return
  }
  saving.value = true
  try {
    await createTask({
      order_id: form.order_id,
      driver_account_id: form.driver_account_id,
      vehicle_id: form.vehicle_id,
      planned_load_at: toIso(form.planned_load_at),
      planned_deliver_at: toIso(form.planned_deliver_at),
      notes: form.notes,
    })
    ElMessage.success('运输任务已创建，等待司机确认')
    createVisible.value = false
    await load()
  } catch (error) {
    report(error, '派单失败')
  } finally {
    saving.value = false
  }
}

function openRedispatch(row: TransportTask): void {
  targetTask.value = row
  Object.assign(redispatchForm, {
    driver_account_id: null,
    vehicle_id: null,
    reason: '',
  })
  redispatchVisible.value = true
}

async function submitRedispatch(): Promise<void> {
  const task = targetTask.value
  if (!task || redispatchForm.driver_account_id === null || redispatchForm.vehicle_id === null) {
    ElMessage.warning('请选择新的司机与车辆')
    return
  }
  if (!redispatchForm.reason.trim()) {
    ElMessage.warning('请填写重新派单原因')
    return
  }
  saving.value = true
  try {
    await redispatchTask(task.id, {
      driver_account_id: redispatchForm.driver_account_id,
      vehicle_id: redispatchForm.vehicle_id,
      reason: redispatchForm.reason,
    })
    ElMessage.success('已重新派单并留存原新记录')
    redispatchVisible.value = false
    await load()
  } catch (error) {
    report(error, '重新派单失败')
  } finally {
    saving.value = false
  }
}

async function openHistory(row: TransportTask): Promise<void> {
  try {
    historyRows.value = await dispatchHistory(row.id)
    historyVisible.value = true
  } catch (error) {
    report(error, '读取派单历史失败')
  }
}

function canRedispatch(row: TransportTask): boolean {
  return (['待司机确认', '待装货'] as TaskStatus[]).includes(row.status)
}
</script>

<template>
  <section class="dispatch">
    <h1 class="page-title">派单管理</h1>
    <p class="page-note">为已承接订单创建运输任务；已起运任务须走运输异常流程，不能在此变更。</p>

    <h2 class="section-title">待派单订单</h2>
    <el-table :data="orders" border v-loading="loading" class="table">
      <el-table-column prop="order_no" label="订单号" width="170" />
      <el-table-column prop="cargo_name" label="货物" width="140" />
      <el-table-column prop="vehicle_type" label="车型要求" width="120" />
      <el-table-column prop="load_requirement" label="载重要求" width="130" />
      <el-table-column prop="quote_amount_yuan" label="报价(元)" width="110" />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }: { row: Order }">
          <el-button link type="primary" @click="openCreate(row)">派单</el-button>
        </template>
      </el-table-column>
      <template #empty>暂无待派单订单</template>
    </el-table>

    <h2 class="section-title">运输任务</h2>
    <el-table :data="tasks" border class="table">
      <el-table-column prop="task_no" label="任务号" width="170" />
      <el-table-column prop="order_no" label="订单号" width="170" />
      <el-table-column prop="driver_name" label="司机" width="100" />
      <el-table-column prop="vehicle_plate" label="车牌" width="110" />
      <el-table-column prop="planned_load_at" label="计划装货" width="180" />
      <el-table-column prop="planned_deliver_at" label="计划送达" width="180" />
      <el-table-column prop="status" label="任务状态" width="110" />
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }: { row: TransportTask }">
          <el-button link type="primary" :disabled="!canRedispatch(row)" @click="openRedispatch(row)">
            重新派单
          </el-button>
          <el-button link @click="openHistory(row)">派单历史</el-button>
        </template>
      </el-table-column>
      <template #empty>暂无运输任务</template>
    </el-table>

    <el-dialog v-model="createVisible" title="创建运输任务" width="620px">
      <el-form label-width="120px">
        <el-form-item label="运输订单" required>
          <el-select v-model="form.order_id" placeholder="选择已承接订单">
            <el-option
              v-for="order in orders"
              :key="order.id"
              :label="`${order.order_no} · ${order.cargo_name}`"
              :value="order.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="司机" required>
          <el-select v-model="form.driver_account_id" placeholder="选择可派单司机">
            <el-option
              v-for="driver in drivers"
              :key="driver.account_id"
              :label="`${driver.name}（${driver.phone}）`"
              :value="driver.account_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="车辆" required>
          <el-select v-model="form.vehicle_id" placeholder="选择可用车辆">
            <el-option
              v-for="vehicle in vehicles"
              :key="vehicle.id"
              :label="`${vehicle.plate_no} · ${vehicle.vehicle_type}`"
              :value="vehicle.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="计划装货" required>
          <el-input v-model="form.planned_load_at" placeholder="2026-11-23T10:00" />
        </el-form-item>
        <el-form-item label="计划送达" required>
          <el-input v-model="form.planned_deliver_at" placeholder="2026-11-23T18:00" />
        </el-form-item>
        <el-form-item label="注意事项">
          <el-input v-model="form.notes" type="textarea" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">派单</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="redispatchVisible" title="未起运重新派单" width="560px">
      <p class="dialog-note">仅待司机确认 / 待装货可重新派单，原新司机车辆与原因将留存。</p>
      <el-form label-width="100px">
        <el-form-item label="新司机" required>
          <el-select v-model="redispatchForm.driver_account_id" placeholder="选择可派单司机">
            <el-option
              v-for="driver in drivers"
              :key="driver.account_id"
              :label="`${driver.name}（${driver.phone}）`"
              :value="driver.account_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="新车辆" required>
          <el-select v-model="redispatchForm.vehicle_id" placeholder="选择可用车辆">
            <el-option
              v-for="vehicle in vehicles"
              :key="vehicle.id"
              :label="`${vehicle.plate_no} · ${vehicle.vehicle_type}`"
              :value="vehicle.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="原因" required>
          <el-input v-model="redispatchForm.reason" type="textarea" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="redispatchVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitRedispatch">确认重新派单</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="historyVisible" title="派单历史" width="720px">
      <el-table :data="historyRows" border>
        <el-table-column prop="dispatch_no" label="记录号" width="170" />
        <el-table-column prop="action" label="动作" width="100" />
        <el-table-column prop="original_driver_name" label="原司机" width="100" />
        <el-table-column prop="new_driver_name" label="新司机" width="100" />
        <el-table-column prop="original_vehicle_plate" label="原车牌" width="110" />
        <el-table-column prop="new_vehicle_plate" label="新车牌" width="110" />
        <el-table-column prop="reason" label="原因" min-width="140" />
        <el-table-column prop="created_at" label="时间" width="180" />
      </el-table>
    </el-dialog>
  </section>
</template>

<style scoped>
.dispatch {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.page-note,
.dialog-note {
  margin: var(--space-1) 0 var(--space-6);
  color: var(--color-text-muted);
}

.section-title {
  margin: var(--space-6) 0 var(--space-3);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.table {
  width: 100%;
}
</style>
