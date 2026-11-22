<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import {
  createDriver,
  listDrivers,
  setDriverAccountStatus,
  setDriverAvailability,
  setDriverEmployment,
  updateDriver,
} from '@/api/driver'
import type {
  AccountStatus,
  Availability,
  Driver,
  DriverCreatePayload,
  DriverUpdatePayload,
  Employment,
} from '@/types/driver'

const drivers = ref<Driver[]>([])
const loading = ref(false)
const saving = ref(false)
const filter = reactive<{
  availability?: Availability
  employment?: Employment
  account_status?: AccountStatus
}>({})

const createVisible = ref(false)
const editVisible = ref(false)
const statusVisible = ref(false)
const editing = ref<Driver | null>(null)
const statusTarget = ref<Driver | null>(null)

const createForm = reactive<DriverCreatePayload>({
  phone: '',
  password: '',
  name: '',
  id_number: '',
  license_no: '',
  license_type: '',
  license_expiry: '',
})
const editForm = reactive<DriverUpdatePayload>({
  name: '',
  id_number: '',
  license_no: '',
  license_type: '',
  license_expiry: '',
})
const statusForm = reactive({
  availability: '可派单' as Availability,
  employment: '在职' as Employment,
  account_status: '正常使用' as AccountStatus,
})

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    drivers.value = await listDrivers({ ...filter })
  } catch (error) {
    report(error, '读取司机列表失败')
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
    phone: '',
    password: '',
    name: '',
    id_number: '',
    license_no: '',
    license_type: '',
    license_expiry: '',
  })
  createVisible.value = true
}

async function submitCreate(): Promise<void> {
  saving.value = true
  try {
    await createDriver({ ...createForm })
    ElMessage.success('司机已创建，首次登录须改密并完成身份绑定')
    createVisible.value = false
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
    name: row.name,
    id_number: row.id_number,
    license_no: row.license_no,
    license_type: row.license_type,
    license_expiry: row.license_expiry,
  })
  editVisible.value = true
}

async function submitEdit(): Promise<void> {
  if (!editing.value) return
  saving.value = true
  try {
    await updateDriver(editing.value.account_id, { ...editForm })
    ElMessage.success('司机资料已保存')
    editVisible.value = false
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
  statusVisible.value = true
}

async function submitStatus(): Promise<void> {
  const target = statusTarget.value
  if (!target) return
  saving.value = true
  try {
    if (statusForm.availability !== target.availability) {
      await setDriverAvailability(target.account_id, statusForm.availability)
    }
    if (statusForm.account_status !== target.account_status) {
      await setDriverAccountStatus(target.account_id, statusForm.account_status)
    }
    if (statusForm.employment !== target.employment) {
      await setDriverEmployment(target.account_id, statusForm.employment)
    }
    ElMessage.success('司机状态已更新')
    statusVisible.value = false
    await load()
  } catch (error) {
    report(error, '更新司机状态失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="drivers">
    <div class="header-row">
      <div>
        <h1 class="page-title">司机管理</h1>
        <p class="page-note">司机由本公司创建并归属本公司，不能自行注册或承接公共货源。</p>
      </div>
      <el-button type="primary" @click="openCreate">新增司机</el-button>
    </div>

    <div class="filter-row">
      <el-select v-model="filter.availability" placeholder="接单可用性" clearable class="filter">
        <el-option v-for="item in ['可派单', '任务占用中', '暂停接单']" :key="item" :value="item" />
      </el-select>
      <el-select v-model="filter.employment" placeholder="雇佣关系" clearable class="filter">
        <el-option v-for="item in ['在职', '离职']" :key="item" :value="item" />
      </el-select>
      <el-select v-model="filter.account_status" placeholder="账号状态" clearable class="filter">
        <el-option v-for="item in ['正常使用', '已禁用']" :key="item" :value="item" />
      </el-select>
      <el-button @click="load">筛选</el-button>
    </div>

    <el-table :data="drivers" border v-loading="loading" class="table">
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="phone" label="电话" width="130" />
      <el-table-column prop="auth_status" label="认证状态" width="110" />
      <el-table-column prop="qualification" label="驾驶资格" width="100" />
      <el-table-column prop="availability" label="接单可用性" width="120" />
      <el-table-column prop="employment" label="雇佣关系" width="100" />
      <el-table-column prop="account_status" label="账号状态" width="100" />
      <el-table-column prop="current_vehicle" label="当前车辆" width="120">
        <template #default="{ row }: { row: Driver }">{{ row.current_vehicle || '—' }}</template>
      </el-table-column>
      <el-table-column prop="current_task" label="当前任务" width="120">
        <template #default="{ row }: { row: Driver }">{{ row.current_task || '—' }}</template>
      </el-table-column>
      <el-table-column prop="historical_task_count" label="历史任务数" width="110" />
      <el-table-column label="操作" fixed="right" width="180">
        <template #default="{ row }: { row: Driver }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="openStatus(row)">状态</el-button>
        </template>
      </el-table-column>
      <template #empty>暂无司机，点击「新增司机」为本公司在册。</template>
    </el-table>

    <el-dialog v-model="createVisible" title="新增司机" width="560px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="手机号" required>
          <el-input v-model="createForm.phone" maxlength="64" />
        </el-form-item>
        <el-form-item label="临时密码" required>
          <el-input v-model="createForm.password" type="password" maxlength="128" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="createForm.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="身份证号">
          <el-input v-model="createForm.id_number" maxlength="64" />
        </el-form-item>
        <el-form-item label="驾驶证号">
          <el-input v-model="createForm.license_no" maxlength="64" />
        </el-form-item>
        <el-form-item label="准驾车型">
          <el-input v-model="createForm.license_type" maxlength="32" />
        </el-form-item>
        <el-form-item label="驾驶证有效期">
          <el-input v-model="createForm.license_expiry" placeholder="ISO 8601 日期" maxlength="32" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑司机资料" width="560px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="姓名" required>
          <el-input v-model="editForm.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="身份证号">
          <el-input v-model="editForm.id_number" maxlength="64" />
        </el-form-item>
        <el-form-item label="驾驶证号">
          <el-input v-model="editForm.license_no" maxlength="64" />
        </el-form-item>
        <el-form-item label="准驾车型">
          <el-input v-model="editForm.license_type" maxlength="32" />
        </el-form-item>
        <el-form-item label="驾驶证有效期">
          <el-input v-model="editForm.license_expiry" maxlength="32" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="statusVisible" title="设置司机状态" width="480px">
      <p class="dialog-note">三类状态相互独立；暂停接单不派新任务，在途任务继续。</p>
      <el-form label-width="100px">
        <el-form-item label="接单可用性">
          <el-select v-model="statusForm.availability">
            <el-option v-for="item in ['可派单', '任务占用中', '暂停接单']" :key="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号状态">
          <el-select v-model="statusForm.account_status">
            <el-option v-for="item in ['正常使用', '已禁用']" :key="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="雇佣关系">
          <el-select v-model="statusForm.employment">
            <el-option v-for="item in ['在职', '离职']" :key="item" :value="item" />
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
.drivers {
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
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.filter {
  width: 160px;
}

.table {
  width: 100%;
}

.dialog-note {
  margin: 0 0 var(--space-4);
  color: var(--color-text-muted);
}
</style>
