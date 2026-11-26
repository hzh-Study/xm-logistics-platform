<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import StatusPill from '@/components/StatusPill.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { DriverSummary, ShipperSummary, VehicleSummary } from '@/types/admin'
import type { CarrierSummary } from '@/types/carrier'

type Tab = '货主' | '物流公司' | '司机' | '车辆'

const tab = ref<Tab>('货主')
const loading = ref(false)
const keyword = ref('')
const authFilter = ref('')
const accountFilter = ref('')
const shippers = ref<ShipperSummary[]>([])
const carriers = ref<CarrierSummary[]>([])
const drivers = ref<DriverSummary[]>([])
const vehicles = ref<VehicleSummary[]>([])
const statusTarget = ref<{ id: number; name: string; current: string } | null>(null)
const statusOpen = ref(false)

async function load(): Promise<void> {
  loading.value = true
  try {
    if (tab.value === '货主') shippers.value = await adminApi.fetchShippers({ company_name: keyword.value, auth_status: authFilter.value || undefined })
    else if (tab.value === '物流公司') carriers.value = await adminApi.listCarriers(authFilter.value || undefined)
    else if (tab.value === '司机') drivers.value = await adminApi.fetchDrivers({ driver_name: keyword.value, auth_status: authFilter.value || undefined })
    else vehicles.value = await adminApi.fetchVehicles({ plate_no: keyword.value, document_review_status: authFilter.value || undefined })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载账号数据失败')
  } finally {
    loading.value = false
  }
}

function switchTab(next: Tab): void {
  tab.value = next
  keyword.value = ''
  authFilter.value = ''
  void load()
}

function visible<T extends { account_status: string }>(list: T[]): T[] {
  return accountFilter.value ? list.filter((item) => item.account_status === accountFilter.value) : list
}

function askStatus(id: number, name: string, current: string): void {
  statusTarget.value = { id, name, current }
  statusOpen.value = true
}

async function toggleStatus(): Promise<void> {
  const target = statusTarget.value
  if (!target) return
  const next = target.current === '已禁用' ? '正常使用' : '已禁用'
  try {
    if (tab.value === '物流公司') {
      await adminApi.setCarrierAccountStatus(target.id, next)
    } else {
      await adminApi.setAccountStatus(target.id, next)
    }
    ElMessage.success(next === '已禁用' ? '账号已禁用，历史业务记录保留' : '账号已恢复')
    statusOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '账号处置失败')
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="平台主体查询" subtitle="管理员只读查询 · 禁用 / 恢复为独立操作" />

    <div class="tabs">
      <button v-for="item in (['货主', '物流公司', '司机', '车辆'] as Tab[])" :key="item" class="tab" :class="{ 'tab--active': tab === item }" type="button" @click="switchTab(item)">
        {{ item }}
      </button>
    </div>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="acc-kw">{{ tab === '车辆' ? '车牌号' : '关键词' }}</label><el-input id="acc-kw" v-model="keyword" placeholder="请输入关键词" clearable /></div>
        <div class="field">
          <label class="field__label" for="acc-auth">认证状态</label>
          <el-select id="acc-auth" v-model="authFilter" placeholder="全部" clearable>
            <el-option v-for="item in ['未提交', '待审核', '审核通过', '审核不通过']" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="acc-status">账号状态</label>
          <el-select id="acc-status" v-model="accountFilter" placeholder="全部" clearable>
            <el-option v-for="item in ['正常使用', '已禁用', '已注销']" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
      </div>
      <div class="filter-actions">
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel" v-if="tab === '货主'">
      <div class="panel-head"><span class="panel-title">货主</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!shippers.length" text="暂无货主" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th class="num">主体编号</th><th>名称</th><th>认证状态</th><th>账号状态</th><th class="num">订单数</th><th class="ops">操作</th></tr></thead>
            <tbody>
              <tr v-for="row in visible(shippers)" :key="row.account_id">
                <td class="num">{{ row.account_id }}</td><td>{{ row.company_name }}</td>
                <td><StatusPill :text="row.auth_status" /></td><td><StatusPill :text="row.account_status" /></td>
                <td class="num">—</td>
                <td class="ops"><el-button type="primary" link @click="askStatus(row.account_id, row.company_name, row.account_status)">{{ row.account_status === '已禁用' ? '恢复' : '禁用' }}</el-button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="panel" v-else-if="tab === '物流公司'">
      <div class="panel-head"><span class="panel-title">物流公司</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!carriers.length" text="暂无物流公司" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th class="num">主体编号</th><th>企业名称</th><th>认证状态</th><th>账号状态</th><th class="num">司机数</th><th class="ops">操作</th></tr></thead>
            <tbody>
              <tr v-for="row in visible(carriers)" :key="row.account_id">
                <td class="num">{{ row.account_id }}</td><td>{{ row.company_name }}</td>
                <td><StatusPill :text="row.auth_status" /></td><td><StatusPill :text="row.account_status" /></td>
                <td class="num">—</td>
                <td class="ops"><el-button type="primary" link @click="askStatus(row.account_id, row.company_name, row.account_status)">{{ row.account_status === '已禁用' ? '恢复' : '禁用' }}</el-button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="panel" v-else-if="tab === '司机'">
      <div class="panel-head"><span class="panel-title">司机</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!drivers.length" text="暂无司机" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th class="num">主体编号</th><th>姓名</th><th>认证状态</th><th>账号状态</th><th>所属公司</th><th class="ops">操作</th></tr></thead>
            <tbody>
              <tr v-for="row in visible(drivers)" :key="row.account_id">
                <td class="num">{{ row.account_id }}</td><td>{{ row.driver_name }}</td>
                <td><StatusPill :text="row.auth_status" /></td><td><StatusPill :text="row.account_status" /></td>
                <td>{{ row.carrier_id ? `公司 #${row.carrier_id}` : '—' }}</td>
                <td class="ops"><el-button type="primary" link @click="askStatus(row.account_id, row.driver_name, row.account_status)">{{ row.account_status === '已禁用' ? '恢复' : '禁用' }}</el-button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="panel" v-else>
      <div class="panel-head"><span class="panel-title">车辆</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!vehicles.length" text="暂无车辆" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th class="num">车辆编号</th><th>车牌号</th><th>生命周期</th><th>可用性</th><th>所属公司</th><th class="ops">操作</th></tr></thead>
            <tbody>
              <tr v-for="row in vehicles" :key="row.id">
                <td class="num">{{ row.id }}</td><td class="num">{{ row.plate_no }}</td>
                <td><StatusPill :text="row.lifecycle" /></td><td><StatusPill :text="row.availability" /></td>
                <td>公司 #{{ row.carrier_id }}</td>
                <td class="ops">—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <ConfirmDialog v-model="statusOpen" :title="statusTarget?.current === '已禁用' ? '恢复账号' : '禁用主体'" :confirm-text="statusTarget?.current === '已禁用' ? '确认恢复' : '确认禁用'" danger @confirm="toggleStatus">
      禁用后该主体账号状态变为「已禁用」，历史业务记录保留；可随时恢复。
    </ConfirmDialog>
  </section>
</template>

<style scoped>
.tabs { display: flex; gap: var(--space-6); border-bottom: 1px solid var(--color-border); margin-bottom: var(--space-4); }
.tab { padding: var(--space-3) 0; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--color-text-2); font-size: var(--font-size-md); cursor: pointer; margin-bottom: -1px; }
.tab--active { color: var(--color-accent); border-bottom-color: var(--color-accent); font-weight: 500; }
</style>
