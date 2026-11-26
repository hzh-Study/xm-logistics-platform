<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import { createTask, dispatchHistory, listCarrierOrders, listTasks, redispatchTask } from '@/api/dispatch'
import { listDrivers } from '@/api/driver'
import { listVehicles } from '@/api/vehicle'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { Driver } from '@/types/driver'
import type { Order } from '@/types/order'
import type { Vehicle } from '@/types/vehicle'
import type { DispatchHistory, TaskStatus, TransportTask } from '@/types/dispatch'

const router = useRouter()
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
const orderKeyword = ref('')
const shipPlace = ref('')
const recvPlace = ref('')
const acceptedFrom = ref('')

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

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

const pendingOrders = ref<Order[]>([])
const dispatchedTasks = ref<TransportTask[]>([])

async function load(): Promise<void> {
  loading.value = true
  try {
    const [orderRows, taskRows, driverRows, vehicleRows] = await Promise.all([
      listCarrierOrders(), listTasks(), listDrivers(), listVehicles({ assignable: true }),
    ])
    pendingOrders.value = orderRows.filter((row) => row.status === '已承接')
    tasks.value = taskRows
    drivers.value = driverRows.filter((row) => row.can_dispatch_new)
    vehicles.value = vehicleRows
    applyFilter()
  } catch (error) {
    report(error, '读取派单数据失败')
  } finally {
    loading.value = false
  }
}

function applyFilter(): void {
  dispatchedTasks.value = tasks.value.filter((task) => {
    const order = pendingOrders.value.find((item) => item.id === task.order_id)
    const ship = order ? `${order.shipping_snapshot.province}${order.shipping_snapshot.city}` : ''
    const recv = order ? `${order.receiving_snapshot.province}${order.receiving_snapshot.city}` : ''
    const orderNo = task.order_no
    const placeMatch = !shipPlace.value || ship.includes(shipPlace.value)
    const recvMatch = !recvPlace.value || recv.includes(recvPlace.value)
    const noMatch = !orderKeyword.value || orderNo.includes(orderKeyword.value)
    const dateMatch = !acceptedFrom.value || stamp(order?.accepted_at ?? '').slice(0, 10) >= acceptedFrom.value
    return placeMatch && recvMatch && noMatch && dateMatch
  })
}

function resetFilter(): void {
  orderKeyword.value = ''
  shipPlace.value = ''
  recvPlace.value = ''
  acceptedFrom.value = ''
  applyFilter()
}

function report(error: unknown, fallback: string): void {
  if (error instanceof ApiError && Array.isArray(error.details)) {
    const first = error.details[0] as { field?: string; message?: string }
    ElMessage.error(`${first.field ?? '字段'}：${first.message ?? fallback}`)
    return
  }
  ElMessage.error(error instanceof Error ? error.message : fallback)
}

function toIso(value: string): string {
  if (!value) return ''
  return value.length === 16 ? `${value}:00+00:00` : value
}

function openCreate(order?: Order): void {
  Object.assign(form, {
    order_id: order?.id ?? null, driver_account_id: null, vehicle_id: null,
    planned_load_at: '', planned_deliver_at: '', notes: '',
  })
  createVisible.value = true
}

async function submitCreate(): Promise<void> {
  if (form.order_id === null || form.driver_account_id === null || form.vehicle_id === null) {
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
  Object.assign(redispatchForm, { driver_account_id: null, vehicle_id: null, reason: '' })
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

function place(order: Order): string {
  return `${order.shipping_snapshot.province}${order.shipping_snapshot.city} → ${order.receiving_snapshot.province}${order.receiving_snapshot.city}`
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="派单管理" :subtitle="`待派单 ${pendingOrders.length} · 已派单 ${tasks.length}`">
      <template #actions><el-button type="primary" @click="openCreate()">新建派单</el-button></template>
    </PageHeader>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="dp-no">订单编号</label><el-input id="dp-no" v-model="orderKeyword" placeholder="请输入订单编号" clearable /></div>
        <div class="field"><label class="field__label" for="dp-ship">发货地</label><el-input id="dp-ship" v-model="shipPlace" placeholder="请输入发货地" clearable /></div>
        <div class="field"><label class="field__label" for="dp-recv">收货地</label><el-input id="dp-recv" v-model="recvPlace" placeholder="请输入收货地" clearable /></div>
        <div class="field"><label class="field__label">承接时间</label><el-date-picker v-model="acceptedFrom" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" class="date-input" /></div>
      </div>
      <div class="filter-actions">
        <el-button @click="resetFilter">重置</el-button>
        <el-button type="primary" @click="applyFilter">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">待派单运输订单</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!pendingOrders.length" text="暂无待派单的运输订单" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">订单编号</th><th>货物</th><th>发货地 → 收货地</th><th class="num">计划装货</th><th class="num">承接时间</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="order in pendingOrders" :key="order.id">
                <td class="num">{{ order.order_no }}</td>
                <td>{{ [order.cargo_name, order.quantity, order.weight].filter(Boolean).join(' · ') }}</td>
                <td>{{ place(order) }}</td>
                <td class="num">—（未排期）</td>
                <td class="num">{{ stamp(order.accepted_at ?? '') }}</td>
                <td class="ops">
                  <el-button type="primary" link @click="openCreate(order)">派单</el-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">已派单任务</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!dispatchedTasks.length" text="暂无已派单任务" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">任务编号</th><th>订单 / 货物</th><th>司机 / 车辆</th><th>任务状态</th><th class="num">计划装货</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="task in dispatchedTasks" :key="task.id">
                <td class="num">{{ task.task_no }}</td>
                <td>{{ task.order_no }}<div class="cell-sub">{{ task.notes || '—' }}</div></td>
                <td>{{ task.driver_name }} / {{ task.vehicle_plate }}</td>
                <td><StatusPill :text="task.status" /></td>
                <td class="num">{{ stamp(task.planned_load_at) }}</td>
                <td class="ops">
                  <el-button type="primary" link @click="router.push(`/carrier/tasks/${task.id}/progress`)">查看详情</el-button>
                  <el-button v-if="canRedispatch(task)" type="primary" link @click="openRedispatch(task)">撤回改派</el-button>
                  <el-button type="primary" link @click="openHistory(task)">派单历史</el-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="createVisible" title="新建派单">
      <template #body>
        <NoticeBar tone="info">派单校验：司机与车辆均须属于本公司且可用、司机具备准驾资格、车辆满足运输要求，且计划时段无冲突。</NoticeBar>
        <form class="drawer-form">
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>运输订单</label>
            <el-select v-model="form.order_id" placeholder="全部" style="width: 100%">
              <el-option v-for="order in pendingOrders" :key="order.id" :label="`${order.order_no} · ${order.cargo_name} ${order.weight || order.quantity || ''}`" :value="order.id" />
            </el-select>
          </div>
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>司机</label>
            <el-select v-model="form.driver_account_id" placeholder="全部" style="width: 100%">
              <el-option v-for="driver in drivers" :key="driver.account_id" :label="`${driver.name} · ${driver.availability} · ${driver.employment}`" :value="driver.account_id" />
            </el-select>
          </div>
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>车辆</label>
            <el-select v-model="form.vehicle_id" placeholder="全部" style="width: 100%">
              <el-option v-for="vehicle in vehicles" :key="vehicle.id" :label="`${vehicle.plate_no} · ${vehicle.availability} · ${vehicle.lifecycle}`" :value="vehicle.id" />
            </el-select>
          </div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>计划装货时间</label><el-date-picker v-model="form.planned_load_at" type="datetime" value-format="YYYY-MM-DDTHH:mm" class="date-input" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>计划送达时间</label><el-date-picker v-model="form.planned_deliver_at" type="datetime" value-format="YYYY-MM-DDTHH:mm" class="date-input" /></div>
          <div class="field"><label class="field__label">派单备注</label><el-input v-model="form.notes" type="textarea" :rows="2" /></div>
        </form>
      </template>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">确认派单</el-button>
      </template>
    </DetailDrawer>

    <DetailDrawer v-model="redispatchVisible" title="撤回改派">
      <template #body>
        <NoticeBar tone="warning">改派将保留原派单记录，并追加新的派单记录，不覆盖原文。</NoticeBar>
        <form class="drawer-form">
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>新司机</label>
            <el-select v-model="redispatchForm.driver_account_id" placeholder="全部" style="width: 100%">
              <el-option v-for="driver in drivers" :key="driver.account_id" :label="`${driver.name} · ${driver.availability}`" :value="driver.account_id" />
            </el-select>
          </div>
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>新车辆</label>
            <el-select v-model="redispatchForm.vehicle_id" placeholder="全部" style="width: 100%">
              <el-option v-for="vehicle in vehicles" :key="vehicle.id" :label="`${vehicle.plate_no} · ${vehicle.availability}`" :value="vehicle.id" />
            </el-select>
          </div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>改派原因</label><el-input v-model="redispatchForm.reason" type="textarea" :rows="3" /></div>
        </form>
      </template>
      <template #footer>
        <el-button @click="redispatchVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitRedispatch">确认改派</el-button>
      </template>
    </DetailDrawer>

    <DetailDrawer v-model="historyVisible" title="派单历史">
      <template #body>
        <ul class="history-list">
          <li v-for="(item, index) in historyRows" :key="item.id ?? index">
            <strong>{{ item.action }}</strong>
            <span>{{ item.original_driver_name || '—' }} → {{ item.new_driver_name || '—' }} · {{ item.original_vehicle_plate || '—' }} → {{ item.new_vehicle_plate || '—' }}</span>
            <span class="meta">{{ item.reason || '—' }} · {{ item.actor }} · {{ stamp(item.created_at) }}</span>
          </li>
        </ul>
        <EmptyState v-if="!historyRows.length" text="暂无派单历史" />
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.date-input { width: 100%; }
.drawer-form { padding-top: var(--space-4); }
.history-list { margin: 0; padding: 0; list-style: none; }
.history-list li { display: flex; flex-direction: column; gap: var(--space-1); padding: var(--space-3) 0; border-bottom: 1px solid var(--color-border); font-size: var(--font-size-sm); }
.history-list li:last-child { border-bottom: 0; }
.history-list .meta { color: var(--color-text-3); font-size: var(--font-size-xs); }
</style>
