<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import type {
  PlatformException,
  PlatformExceptionCategory,
  PlatformExceptionView,
  PlatformResult,
} from '@/types/admin'

const categories: PlatformExceptionCategory[] = [
  '投诉',
  '订单纠纷',
  '公司违规',
  '司机违规',
  '车辆异常',
  '任务长期未完成',
  '费用纠纷',
]
const results: PlatformResult[] = ['已处理', '已调解', '已处罚', '已驳回', '已归档']

const rows = ref<PlatformException[]>([])
const loading = ref(false)
const filter = reactive({ category: '' as PlatformExceptionCategory | '' })
const createVisible = ref(false)
const detailVisible = ref(false)
const detail = ref<PlatformExceptionView | null>(null)

const createForm = reactive({
  category: '投诉' as PlatformExceptionCategory,
  subject: '',
  detail: '',
  subject_account_id: undefined as number | undefined,
  order_id: undefined as number | undefined,
  task_id: undefined as number | undefined,
  vehicle_id: undefined as number | undefined,
})
const handlingForm = reactive({ result: '已处理' as PlatformResult, reason: '', detail: '' })

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await adminApi.fetchPlatformExceptions(filter.category || undefined)
  } catch (error) {
    ElMessage.error(errorText(error, '加载平台异常失败'))
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  createForm.category = '投诉'
  createForm.subject = ''
  createForm.detail = ''
  createForm.subject_account_id = undefined
  createForm.order_id = undefined
  createForm.task_id = undefined
  createForm.vehicle_id = undefined
  createVisible.value = true
}

async function submitCreate(): Promise<void> {
  if (!createForm.subject.trim() || !createForm.detail.trim()) {
    ElMessage.warning('对象描述与异常说明必填')
    return
  }
  try {
    await adminApi.createPlatformException({
      category: createForm.category,
      subject: createForm.subject,
      detail: createForm.detail,
      subject_account_id: createForm.subject_account_id,
      order_id: createForm.order_id,
      task_id: createForm.task_id,
      vehicle_id: createForm.vehicle_id,
    })
    ElMessage.success('平台异常已登记')
    createVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(errorText(error, '登记平台异常失败'))
  }
}

async function openDetail(row: PlatformException): Promise<void> {
  try {
    detail.value = await adminApi.fetchPlatformException(row.id)
    handlingForm.result = '已处理'
    handlingForm.reason = ''
    handlingForm.detail = ''
    detailVisible.value = true
  } catch (error) {
    ElMessage.error(errorText(error, '读取平台异常详情失败'))
  }
}

async function submitHandling(): Promise<void> {
  if (!detail.value || !handlingForm.reason.trim()) {
    ElMessage.warning('处理结果原因必填')
    return
  }
  try {
    await adminApi.appendPlatformHandling(detail.value.exception.id, {
      result: handlingForm.result,
      reason: handlingForm.reason,
      detail: handlingForm.detail,
    })
    ElMessage.success('异常处理记录已追加')
    detail.value = await adminApi.fetchPlatformException(detail.value.exception.id)
    handlingForm.reason = ''
    handlingForm.detail = ''
    await load()
  } catch (error) {
    ElMessage.error(errorText(error, '追加处理记录失败'))
  }
}

onMounted(load)
</script>

<template>
  <section class="platform-exceptions">
    <h1 class="page-title">平台异常管理</h1>
    <p class="page-note">处理结果以追加方式写入，原始异常记录与既有处理记录均不覆盖。</p>

    <div class="toolbar">
      <el-select v-model="filter.category" class="field" placeholder="全部类别" clearable>
        <el-option v-for="category in categories" :key="category" :label="category" :value="category" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="openCreate">登记异常</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="exception_no" label="异常编号" width="170" />
      <el-table-column label="类别" width="120">
        <template #default="{ row }">
          <el-tag type="warning">{{ row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="subject" label="反映对象" />
      <el-table-column prop="detail" label="异常说明" show-overflow-tooltip />
      <el-table-column prop="actor" label="登记角色" width="100" />
      <el-table-column prop="created_at" label="登记时间" width="200" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button type="primary" link @click="openDetail(row)">处理 / 详情</el-button>
        </template>
      </el-table-column>
      <template #empty><span>暂无符合条件的平台异常。</span></template>
    </el-table>

    <el-dialog v-model="createVisible" title="登记平台异常" width="560px">
      <el-form label-position="top" class="form">
        <el-form-item label="异常类别">
          <el-select v-model="createForm.category" class="field">
            <el-option v-for="category in categories" :key="category" :label="category" :value="category" />
          </el-select>
        </el-form-item>
        <el-form-item label="反映对象">
          <el-input v-model="createForm.subject" maxlength="200" placeholder="如：某物流公司 / 订单" />
        </el-form-item>
        <el-form-item label="异常说明">
          <el-input v-model="createForm.detail" type="textarea" :rows="3" maxlength="2000" placeholder="描述异常情况" />
        </el-form-item>
        <el-form-item label="涉及主体账号 id（可选，用于站内通知）">
          <el-input-number v-model="createForm.subject_account_id" :min="1" controls-position="right" />
        </el-form-item>
        <el-form-item label="关联订单 / 任务 / 车辆 id（可选）">
          <div class="inline">
            <el-input-number v-model="createForm.order_id" :min="1" controls-position="right" placeholder="订单 id" />
            <el-input-number v-model="createForm.task_id" :min="1" controls-position="right" placeholder="任务 id" />
            <el-input-number v-model="createForm.vehicle_id" :min="1" controls-position="right" placeholder="车辆 id" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">登记</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="平台异常处理" width="720px">
      <template v-if="detail">
        <div class="original">
          <p class="detail-row">异常编号：{{ detail.exception.exception_no }} · 类别：{{ detail.exception.category }}</p>
          <p class="detail-row">反映对象：{{ detail.exception.subject }}</p>
          <p class="detail-row">异常说明：{{ detail.exception.detail }}</p>
          <p class="detail-row">登记角色：{{ detail.exception.actor }} · 登记时间：{{ detail.exception.created_at }}</p>
        </div>

        <h3 class="section-title">处理记录（追加，不覆盖）</h3>
        <el-table :data="detail.handling_records" row-key="id" size="small">
          <el-table-column prop="result" label="处理结果" width="100">
            <template #default="{ row }"><el-tag type="success">{{ row.result }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="reason" label="原因" show-overflow-tooltip />
          <el-table-column prop="actor" label="处理角色" width="100" />
          <el-table-column prop="handled_at" label="处理时间" width="200" />
          <template #empty><span>尚无处理记录，可在下方追加。</span></template>
        </el-table>

        <h3 class="section-title">追加处理记录</h3>
        <el-form label-position="top" class="form">
          <el-form-item label="处理结果">
            <el-select v-model="handlingForm.result" class="field">
              <el-option v-for="result in results" :key="result" :label="result" :value="result" />
            </el-select>
          </el-form-item>
          <el-form-item label="处理原因">
            <el-input v-model="handlingForm.reason" type="textarea" :rows="2" maxlength="1000" placeholder="写明处理依据与结论" />
          </el-form-item>
          <el-form-item label="处理说明（可选）">
            <el-input v-model="handlingForm.detail" type="textarea" :rows="2" maxlength="2000" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="submitHandling">追加处理记录</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.platform-exceptions {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0 0 var(--space-1);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.page-note {
  margin: 0 0 var(--space-6);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.field {
  width: 200px;
}

.form {
  margin-top: var(--space-2);
}

.inline {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.original {
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius);
}

.detail-row {
  margin: 0 0 var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.section-title {
  margin: var(--space-4) 0 var(--space-2);
  font-size: var(--font-size-md);
  font-weight: 600;
}
</style>
