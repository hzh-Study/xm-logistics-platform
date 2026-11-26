<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormItemRule } from 'element-plus'
import * as warehouseApi from '@/api/warehouse'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { Warehouse, WarehouseInput, WarehouseStatus } from '@/types/warehouse'

const allRows = ref<Warehouse[]>([])
const loading = ref(false)
const keyword = ref('')
const province = ref('')
const typeFilter = ref('')
const statusFilter = ref<WarehouseStatus | ''>('')
const page = ref(1)
const pageSize = 10

const drawerOpen = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance | null>(null)
const form = reactive<WarehouseInput>(emptyForm())

const rules: Record<string, FormItemRule[]> = {
  name: [{ required: true, message: '请填写仓库名称', trigger: 'blur' }],
  contact: [{ required: true, message: '请填写仓库联系人', trigger: 'blur' }],
  phone: [{ required: true, message: '请填写联系电话', trigger: 'blur' }],
  province: [{ required: true, message: '请填写所在省份', trigger: 'blur' }],
  city: [{ required: true, message: '请填写所在城市', trigger: 'blur' }],
  district: [{ required: true, message: '请填写所在区县', trigger: 'blur' }],
  detail_address: [{ required: true, message: '请填写详细地址', trigger: 'blur' }],
  type: [{ required: true, message: '请填写仓库类型', trigger: 'blur' }],
}

const drawerTitle = computed(() => (editingId.value === null ? '新增仓库' : '修改仓库'))

const rows = computed(() =>
  allRows.value.filter((row) => {
    const provinceMatch = !province.value || row.province.includes(province.value) || row.location.includes(province.value)
    const typeMatch = !typeFilter.value || row.type === typeFilter.value
    return provinceMatch && typeMatch
  }),
)

const pageRows = computed(() => rows.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const pageCount = computed(() => Math.max(1, Math.ceil(rows.value.length / pageSize)))

function emptyForm(): WarehouseInput {
  return { name: '', contact: '', phone: '', province: '', city: '', district: '', detail_address: '', type: '', remarks: '' }
}

function failure(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    allRows.value = await warehouseApi.fetchWarehouses(keyword.value || undefined, statusFilter.value || undefined)
    page.value = 1
  } catch (error) {
    ElMessage.error(failure(error))
  } finally {
    loading.value = false
  }
}

function reset(): void {
  keyword.value = ''
  province.value = ''
  typeFilter.value = ''
  statusFilter.value = ''
  void load()
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  drawerOpen.value = true
}

function openEdit(row: Warehouse): void {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name, contact: row.contact, phone: row.phone,
    province: row.province, city: row.city, district: row.district,
    detail_address: row.detail_address, type: row.type, remarks: row.remarks,
  })
  drawerOpen.value = true
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
    drawerOpen.value = false
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
    await ElMessageBox.confirm(`确认${label}仓库「${row.name}」？`, label, { type: 'warning' })
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
  <section>
    <PageHeader title="仓库管理" subtitle="发货地点主数据，可停用或删除；已固化在订单上的发货快照不受影响">
      <template #actions><el-button type="primary" @click="openCreate">新增仓库</el-button></template>
    </PageHeader>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field">
          <label class="field__label" for="wh-name">仓库名称</label>
          <el-input id="wh-name" v-model="keyword" placeholder="请输入仓库名称" clearable />
        </div>
        <div class="field">
          <label class="field__label" for="wh-province">所在地区</label>
          <el-input id="wh-province" v-model="province" placeholder="如：上海市" clearable />
        </div>
        <div class="field">
          <label class="field__label" for="wh-type">仓库类型</label>
          <el-select id="wh-type" v-model="typeFilter" placeholder="全部" clearable>
            <el-option label="自有仓" value="自有仓" />
            <el-option label="租用仓" value="租用仓" />
            <el-option label="第三方仓" value="第三方仓" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="wh-status">状态</label>
          <el-select id="wh-status" v-model="statusFilter" placeholder="全部" clearable>
            <el-option label="启用" value="正常" />
            <el-option label="停用" value="停用" />
          </el-select>
        </div>
      </div>
      <div class="filter-actions">
        <el-button @click="reset">重置</el-button>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">仓库列表</span><span class="panel-hint">共 {{ rows.length }} 个仓库</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!pageRows.length" text="暂无仓库，点击「新增仓库」创建第一个发货仓库。" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>仓库名称</th><th>所在地区</th><th>详细地址</th><th>联系人 / 电话</th><th>类型</th><th>状态</th><th class="ops">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in pageRows" :key="row.id">
                <td>{{ row.name }}<div v-if="row.remarks" class="cell-sub">{{ row.remarks }}</div></td>
                <td>{{ row.province }} / {{ row.city }}</td>
                <td>{{ row.detail_address }}</td>
                <td class="num">{{ row.contact }} / {{ row.phone }}</td>
                <td>{{ row.type }}</td>
                <td><StatusPill :text="row.status === '正常' ? '启用' : '停用'" /></td>
                <td class="ops">
                  <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
                  <el-button type="primary" link @click="setStatus(row)">{{ row.status === '正常' ? '停用' : '启用' }}</el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="pagination">
            <span>共 {{ rows.length }} 条</span>
            <el-button link :disabled="page <= 1" @click="page--">‹</el-button>
            <span>{{ page }} / {{ pageCount }}</span>
            <el-button link :disabled="page >= pageCount" @click="page++">›</el-button>
          </div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="drawerOpen" :title="drawerTitle">
      <template #body>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <div class="form-grid">
            <div class="field">
              <label class="field__label"><span class="field__req">*</span>仓库名称</label>
              <el-input v-model="form.name" placeholder="请输入仓库名称" />
            </div>
            <div class="field">
              <label class="field__label"><span class="field__req">*</span>联系人</label>
              <el-input v-model="form.contact" placeholder="请输入仓库联系人" />
            </div>
            <div class="field">
              <label class="field__label"><span class="field__req">*</span>联系电话</label>
              <el-input v-model="form.phone" placeholder="请输入联系电话" />
            </div>
            <div class="field">
              <label class="field__label"><span class="field__req">*</span>仓库类型</label>
              <el-select v-model="form.type" placeholder="请选择仓库类型">
                <el-option label="自有仓" value="自有仓" />
                <el-option label="租用仓" value="租用仓" />
                <el-option label="第三方仓" value="第三方仓" />
              </el-select>
            </div>
            <div class="field"><label class="field__label"><span class="field__req">*</span>省份</label><el-input v-model="form.province" /></div>
            <div class="field"><label class="field__label"><span class="field__req">*</span>城市</label><el-input v-model="form.city" /></div>
            <div class="field"><label class="field__label"><span class="field__req">*</span>区县</label><el-input v-model="form.district" /></div>
            <div class="field field--wide">
              <label class="field__label"><span class="field__req">*</span>详细地址</label>
              <el-input v-model="form.detail_address" placeholder="街道、门牌号等" />
            </div>
            <div class="field field--wide">
              <label class="field__label">备注</label>
              <el-input v-model="form.remarks" type="textarea" :rows="2" placeholder="可填写库区、作业时间等说明" />
            </div>
          </div>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="drawerOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSubmit">保存</el-button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.field--wide { grid-column: 1 / -1; }
</style>
