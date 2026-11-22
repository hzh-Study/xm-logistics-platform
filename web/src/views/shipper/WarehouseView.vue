<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as warehouseApi from '@/api/warehouse'
import type { Warehouse, WarehouseInput, WarehouseStatus } from '@/types/warehouse'

interface FormHandle {
  validate: () => Promise<void>
}

const rows = ref<Warehouse[]>([])
const loading = ref(false)
const keyword = ref('')
const statusFilter = ref<WarehouseStatus | ''>('')
const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormHandle | null>(null)
const form = reactive<WarehouseInput>(emptyForm())

const dialogTitle = computed(() =>
  editingId.value === null ? '新增仓库' : '修改仓库',
)

const rules = {
  name: [{ required: true, message: '请填写仓库名称', trigger: 'blur' }],
  contact: [{ required: true, message: '请填写仓库联系人', trigger: 'blur' }],
  phone: [{ required: true, message: '请填写联系电话', trigger: 'blur' }],
  province: [{ required: true, message: '请填写所在省份', trigger: 'blur' }],
  city: [{ required: true, message: '请填写所在城市', trigger: 'blur' }],
  district: [{ required: true, message: '请填写所在区县', trigger: 'blur' }],
  detail_address: [{ required: true, message: '请填写详细地址', trigger: 'blur' }],
  type: [{ required: true, message: '请填写仓库类型', trigger: 'blur' }],
}

function emptyForm(): WarehouseInput {
  return {
    name: '',
    contact: '',
    phone: '',
    province: '',
    city: '',
    district: '',
    detail_address: '',
    type: '',
    remarks: '',
  }
}

function failure(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await warehouseApi.fetchWarehouses(
      keyword.value || undefined,
      statusFilter.value || undefined,
    )
  } catch (error) {
    ElMessage.error(failure(error))
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogOpen.value = true
}

function openEdit(row: Warehouse): void {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    contact: row.contact,
    phone: row.phone,
    province: row.province,
    city: row.city,
    district: row.district,
    detail_address: row.detail_address,
    type: row.type,
    remarks: row.remarks,
  })
  dialogOpen.value = true
}

async function onSubmit(): Promise<void> {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    if (editingId.value === null) {
      await warehouseApi.createWarehouse({ ...form })
      ElMessage.success('仓库已创建')
    } else {
      await warehouseApi.updateWarehouse(editingId.value, { ...form })
      ElMessage.success('仓库已更新')
    }
    dialogOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(failure(error))
  } finally {
    saving.value = false
  }
}

async function setStatus(row: Warehouse): Promise<void> {
  const disable = row.status === '正常'
  const label = disable ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(`确认${label}仓库「${row.name}」？`, label, {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    if (disable) await warehouseApi.disableWarehouse(row.id)
    else await warehouseApi.enableWarehouse(row.id)
    ElMessage.success(`仓库已${label}`)
    await load()
  } catch (error) {
    ElMessage.error(failure(error))
  }
}

onMounted(load)
</script>

<template>
  <section class="warehouse">
    <h1 class="page-title">仓库管理</h1>
    <div class="toolbar">
      <el-input
        v-model="keyword"
        class="search"
        placeholder="按仓库名称搜索"
        clearable
        @keyup.enter="load"
      />
      <el-select v-model="statusFilter" class="filter" placeholder="全部状态" clearable>
        <el-option label="正常" value="正常" />
        <el-option label="停用" value="停用" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="openCreate">新增仓库</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="name" label="仓库名称" />
      <el-table-column prop="location" label="仓库位置" />
      <el-table-column prop="contact" label="联系人" />
      <el-table-column prop="phone" label="联系电话" />
      <el-table-column prop="type" label="仓库类型" />
      <el-table-column prop="status" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.status === '正常' ? 'success' : 'info'">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEdit(row)">修改</el-button>
          <el-button
            :type="row.status === '正常' ? 'danger' : 'success'"
            link
            @click="setStatus(row)"
          >
            {{ row.status === '正常' ? '停用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <span>暂无仓库，点击「新增仓库」创建第一个发货仓库。</span>
      </template>
    </el-table>

    <el-dialog v-model="dialogOpen" :title="dialogTitle" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="仓库名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入仓库名称" />
        </el-form-item>
        <el-form-item label="联系人" prop="contact">
          <el-input v-model="form.contact" placeholder="请输入仓库联系人" />
        </el-form-item>
        <el-form-item label="联系电话" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入联系电话" />
        </el-form-item>
        <el-form-item label="所在省份" prop="province">
          <el-input v-model="form.province" placeholder="请输入省份" />
        </el-form-item>
        <el-form-item label="所在城市" prop="city">
          <el-input v-model="form.city" placeholder="请输入城市" />
        </el-form-item>
        <el-form-item label="所在区县" prop="district">
          <el-input v-model="form.district" placeholder="请输入区县" />
        </el-form-item>
        <el-form-item label="详细地址" prop="detail_address">
          <el-input v-model="form.detail_address" placeholder="街道、门牌号等" />
        </el-form-item>
        <el-form-item label="仓库类型" prop="type">
          <el-input v-model="form.type" placeholder="如：普通仓库、冷链仓库" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.remarks"
            type="textarea"
            :rows="2"
            placeholder="可填写库区、作业时间等说明"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.warehouse {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.search {
  width: 240px;
}

.filter {
  width: 140px;
}
</style>
