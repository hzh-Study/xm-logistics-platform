<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import { createDriver, listDrivers, setDriverAccountStatus, setDriverAvailability, setDriverEmployment, updateDriver } from '@/api/driver'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { AccountStatus, Availability, Driver, DriverCreatePayload, DriverUpdatePayload, Employment } from '@/types/driver'

const drivers = ref<Driver[]>([])
const loading = ref(false)
const saving = ref(false)
const filter = reactive<{ name?: string; availability?: Availability; employment?: Employment; account_status?: AccountStatus }>({})
const phoneKeyword = ref('')

const createOpen = ref(false)
const editOpen = ref(false)
const statusOpen = ref(false)
const editing = ref<Driver | null>(null)
const statusTarget = ref<Driver | null>(null)

const createForm = reactive<DriverCreatePayload>({
  phone: '', password: '', name: '', id_number: '', license_no: '', license_type: '', license_expiry: '',
})
const editForm = reactive<DriverUpdatePayload>({ name: '', id_number: '', license_no: '', license_type: '', license_expiry: '' })
const statusForm = reactive({
  availability: '可派单' as Availability,
  employment: '在职' as Employment,
  account_status: '正常使用' as AccountStatus,
})

const LICENSE_TYPES = ['A1', 'A2', 'B2', 'C1']

const filtered = () => drivers.value.filter((driver) =>
  (!filter.name || driver.name.includes(filter.name)) &&
  (!phoneKeyword.value || driver.phone.includes(phoneKeyword.value)) &&
  (!filter.availability || driver.availability === filter.availability) &&
  (!filter.employment || driver.employment === filter.employment),
)

async function load(): Promise<void> {
  loading.value = true
  try {
    drivers.value = await listDrivers({ availability: filter.availability, employment: filter.employment, account_status: filter.account_status })
  } catch (error) {
    report(error, '读取司机列表失败')
  } finally {
    loading.value = false
  }
}

function reset(): void {
  filter.name = ''
  phoneKeyword.value = ''
  filter.availability = undefined
  filter.employment = undefined
  filter.account_status = undefined
  void load()
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
  Object.assign(createForm, { phone: '', password: '', name: '', id_number: '', license_no: '', license_type: '', license_expiry: '' })
  createOpen.value = true
}

async function submitCreate(): Promise<void> {
  if (!createForm.phone.trim() || !createForm.name.trim() || createForm.password.length < 8) {
    ElMessage.warning('请填写姓名、手机号并设置不少于 8 位的临时密码')
    return
  }
  saving.value = true
  try {
    await createDriver({ ...createForm })
    ElMessage.success('司机已创建，首次登录须改密并完成身份绑定')
    createOpen.value = false
    await load()
  } catch (error) {
    report(error, '创建司机失败')
  } finally {
    saving.value = false
  }
}

function openEdit(row: Driver): void {
  editing.value = row
  Object.assign(editForm, {
    name: row.name, id_number: row.id_number, license_no: row.license_no,
    license_type: row.license_type, license_expiry: row.license_expiry,
  })
  editOpen.value = true
}

async function submitEdit(): Promise<void> {
  if (!editing.value) return
  saving.value = true
  try {
    await updateDriver(editing.value.account_id, { ...editForm })
    ElMessage.success('司机资料已保存')
    editOpen.value = false
    await load()
  } catch (error) {
    report(error, '保存司机资料失败')
  } finally {
    saving.value = false
  }
}

function openStatus(row: Driver): void {
  statusTarget.value = row
  statusForm.availability = row.availability
  statusForm.employment = row.employment
  statusForm.account_status = row.account_status
  statusOpen.value = true
}

async function submitStatus(): Promise<void> {
  const target = statusTarget.value
  if (!target) return
  saving.value = true
  try {
    if (statusForm.availability !== target.availability) await setDriverAvailability(target.account_id, statusForm.availability)
    if (statusForm.account_status !== target.account_status) await setDriverAccountStatus(target.account_id, statusForm.account_status)
    if (statusForm.employment !== target.employment) await setDriverEmployment(target.account_id, statusForm.employment)
    ElMessage.success('司机状态已更新')
    statusOpen.value = false
    await load()
  } catch (error) {
    report(error, '更新司机状态失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="司机管理" :subtitle="`在册司机 ${drivers.length} 人 · 可派单 ${drivers.filter((d) => d.availability === '可派单').length} / 任务占用 ${drivers.filter((d) => d.availability === '任务占用中').length} / 暂停接单 ${drivers.filter((d) => d.availability === '暂停接单').length}`">
      <template #actions><el-button type="primary" @click="openCreate">新增司机</el-button></template>
    </PageHeader>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="dr-name">姓名</label><el-input id="dr-name" v-model="filter.name" placeholder="请输入姓名" clearable /></div>
        <div class="field">
          <label class="field__label" for="dr-auth">认证状态</label>
          <el-select id="dr-auth" v-model="filter.account_status" placeholder="全部" clearable>
            <el-option v-for="item in ['未提交', '待审核', '审核通过', '审核不通过']" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="dr-avail">接单可用性</label>
          <el-select id="dr-avail" v-model="filter.availability" placeholder="全部" clearable>
            <el-option v-for="item in ['可派单', '任务占用中', '暂停接单']" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="dr-emp">雇佣关系</label>
          <el-select id="dr-emp" v-model="filter.employment" placeholder="全部" clearable>
            <el-option label="在职" value="在职" /><el-option label="离职" value="离职" />
          </el-select>
        </div>
        <div class="field"><label class="field__label" for="dr-phone">手机号</label><el-input id="dr-phone" v-model="phoneKeyword" placeholder="请输入手机号" clearable /></div>
      </div>
      <div class="filter-actions">
        <el-button @click="reset">重置</el-button>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">司机列表</span><span class="panel-hint">司机账号由物流公司创建，司机不可自行注册</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!filtered().length" text="暂无司机，点击「新增司机」创建账号。" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th>姓名</th><th class="num">手机号</th><th>认证状态</th><th>接单可用性</th><th>雇佣关系</th><th>当前车辆 / 任务</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in filtered()" :key="row.account_id">
                <td>{{ row.name }}</td>
                <td class="num">{{ row.phone }}</td>
                <td><StatusPill :text="row.auth_status" /></td>
                <td><StatusPill :text="row.availability" /></td>
                <td><StatusPill :text="row.employment" /></td>
                <td>{{ row.current_vehicle || '—' }} / {{ row.current_task || '—' }}</td>
                <td class="ops">
                  <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
                  <el-button type="primary" link @click="openStatus(row)">查看详情</el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ filtered().length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="createOpen" title="新增司机">
      <template #body>
        <NoticeBar tone="info">账号状态、认证状态、接单可用性与雇佣关系为相互独立的四个维度，分开呈现。</NoticeBar>
        <form class="drawer-form">
          <div class="field"><label class="field__label"><span class="field__req">*</span>姓名</label><el-input v-model="createForm.name" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>手机号</label><el-input v-model="createForm.phone" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>临时密码</label><el-input v-model="createForm.password" type="password" show-password /></div>
          <div class="field"><label class="field__label">身份证号</label><el-input v-model="createForm.id_number" /></div>
          <div class="field">
            <label class="field__label">准驾车型</label>
            <el-select v-model="createForm.license_type" placeholder="全部" style="width: 100%">
              <el-option v-for="item in LICENSE_TYPES" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field"><label class="field__label">驾驶证号</label><el-input v-model="createForm.license_no" /></div>
          <div class="field"><label class="field__label">初始状态</label>
            <el-select v-model="statusForm.availability" style="width: 100%">
              <el-option label="可派单" value="可派单" /><el-option label="暂停接单" value="暂停接单" />
            </el-select>
          </div>
        </form>
      </template>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建账号</el-button>
      </template>
    </DetailDrawer>

    <DetailDrawer v-model="editOpen" title="编辑司机资料">
      <template #body>
        <form class="drawer-form">
          <div class="field"><label class="field__label"><span class="field__req">*</span>姓名</label><el-input v-model="editForm.name" /></div>
          <div class="field"><label class="field__label">身份证号</label><el-input v-model="editForm.id_number" /></div>
          <div class="field"><label class="field__label">驾驶证号</label><el-input v-model="editForm.license_no" /></div>
          <div class="field">
            <label class="field__label">准驾车型</label>
            <el-select v-model="editForm.license_type" placeholder="全部" style="width: 100%">
              <el-option v-for="item in LICENSE_TYPES" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field"><label class="field__label">驾驶证有效期</label><el-input v-model="editForm.license_expiry" placeholder="YYYY-MM-DD" /></div>
        </form>
      </template>
      <template #footer>
        <el-button @click="editOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </DetailDrawer>

    <DetailDrawer v-model="statusOpen" :title="`司机详情 · ${statusTarget?.name ?? ''}`">
      <template #body>
        <template v-if="statusTarget">
          <dl class="kv">
            <dt>姓名</dt><dd>{{ statusTarget.name }}</dd>
            <dt>手机号</dt><dd class="num">{{ statusTarget.phone }}</dd>
            <dt>账号状态</dt><dd><StatusPill :text="statusTarget.account_status" /></dd>
            <dt>认证状态</dt><dd><StatusPill :text="statusTarget.auth_status" /></dd>
            <dt>接单可用性</dt><dd><StatusPill :text="statusTarget.availability" /></dd>
            <dt>雇佣关系</dt><dd><StatusPill :text="statusTarget.employment" /></dd>
            <dt>当前车辆 / 任务</dt><dd>{{ statusTarget.current_vehicle || '—' }} / {{ statusTarget.current_task || '—' }}</dd>
          </dl>
          <div class="form-grid section-gap">
            <div class="field">
              <label class="field__label">接单可用性</label>
              <el-select v-model="statusForm.availability" style="width: 100%">
                <el-option v-for="item in ['可派单', '任务占用中', '暂停接单']" :key="item" :label="item" :value="item" />
              </el-select>
            </div>
            <div class="field">
              <label class="field__label">雇佣关系</label>
              <el-select v-model="statusForm.employment" style="width: 100%">
                <el-option label="在职" value="在职" /><el-option label="离职" value="离职" />
              </el-select>
            </div>
            <div class="field">
              <label class="field__label">账号状态</label>
              <el-select v-model="statusForm.account_status" style="width: 100%">
                <el-option label="正常使用" value="正常使用" /><el-option label="已禁用" value="已禁用" />
              </el-select>
            </div>
          </div>
        </template>
      </template>
      <template #footer>
        <el-button @click="statusOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitStatus">保存状态</el-button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.drawer-form { padding-top: var(--space-4); }
.section-gap { margin-top: var(--space-4); }
</style>
