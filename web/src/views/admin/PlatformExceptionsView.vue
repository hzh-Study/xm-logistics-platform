<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { PlatformException, PlatformExceptionCategory, PlatformExceptionView, PlatformResult } from '@/types/admin'

const categories: PlatformExceptionCategory[] = ['投诉', '订单纠纷', '公司违规', '司机违规', '车辆异常', '任务长期未完成', '费用纠纷']
const results: PlatformResult[] = ['已处理', '已调解', '已处罚', '已驳回', '已归档']

const CATEGORY_LABELS: Record<string, string> = {
  公司违规: '物流公司违规', 任务长期未完成: '任务停滞', 费用纠纷: '费用争议',
}

const rows = ref<PlatformException[]>([])
const loading = ref(false)
const filter = reactive({ category: '' as PlatformExceptionCategory | '' })
const createOpen = ref(false)
const saving = ref(false)
const detailOpen = ref(false)
const detail = ref<PlatformExceptionView | null>(null)

const createForm = reactive({
  category: '投诉' as PlatformExceptionCategory, subject: '', detail: '',
  subject_account_id: undefined as number | undefined,
  order_id: undefined as number | undefined,
  task_id: undefined as number | undefined,
  vehicle_id: undefined as number | undefined,
})
const handlingForm = reactive({ result: '已处理' as PlatformResult, reason: '', detail: '' })

function displayCategory(value: string): string {
  return CATEGORY_LABELS[value] ?? value
}

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

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
  Object.assign(createForm, {
    category: '投诉', subject: '', detail: '', subject_account_id: undefined,
    order_id: undefined, task_id: undefined, vehicle_id: undefined,
  })
  createOpen.value = true
}

async function submitCreate(): Promise<void> {
  if (!createForm.subject.trim() || !createForm.detail.trim()) {
    ElMessage.warning('对象描述与异常说明必填')
    return
  }
  saving.value = true
  try {
    await adminApi.createPlatformException({ ...createForm })
    ElMessage.success('平台异常已登记')
    createOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(errorText(error, '登记平台异常失败'))
  } finally {
    saving.value = false
  }
}

async function openDetail(row: PlatformException): Promise<void> {
  try {
    detail.value = await adminApi.fetchPlatformException(row.id)
    handlingForm.result = '已处理'
    handlingForm.reason = ''
    handlingForm.detail = ''
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(errorText(error, '读取平台异常详情失败'))
  }
}

async function submitHandling(): Promise<void> {
  if (!detail.value || !handlingForm.reason.trim()) {
    ElMessage.warning('处理结果原因必填')
    return
  }
  saving.value = true
  try {
    await adminApi.appendPlatformHandling(detail.value.exception.id, { ...handlingForm })
    ElMessage.success('异常处理记录已追加')
    detail.value = await adminApi.fetchPlatformException(detail.value.exception.id)
    handlingForm.reason = ''
    handlingForm.detail = ''
    await load()
  } catch (error) {
    ElMessage.error(errorText(error, '追加处理记录失败'))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="平台异常管理" subtitle="投诉 / 纠纷 / 违规 / 停滞 / 费用争议 · 仅可追加异常处理记录">
      <template #actions><el-button type="primary" @click="openCreate">登记异常</el-button></template>
    </PageHeader>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field">
          <label class="field__label" for="pe-cat">异常类型</label>
          <el-select id="pe-cat" v-model="filter.category" placeholder="全部" clearable>
            <el-option v-for="item in categories" :key="item" :label="displayCategory(item)" :value="item" />
          </el-select>
        </div>
      </div>
      <div class="filter-actions"><el-button type="primary" @click="load">查询</el-button></div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">异常列表</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!rows.length" text="暂无平台异常" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th class="num">异常编号</th><th>异常类型</th><th>关联主体 / 订单</th><th>上报人</th><th class="num">上报时间</th><th class="ops">操作</th></tr></thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id">
                <td class="num">{{ row.exception_no }}</td>
                <td>{{ displayCategory(row.category) }}</td>
                <td>{{ row.subject }}<div v-if="row.order_id" class="cell-sub">订单 #{{ row.order_id }}</div></td>
                <td>{{ row.actor }}</td>
                <td class="num">{{ stamp(row.created_at) }}</td>
                <td class="ops"><el-button type="primary" link @click="openDetail(row)">处置</el-button></td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ rows.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="createOpen" title="登记平台异常">
      <template #body>
        <form class="drawer-form">
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>异常类型</label>
            <el-select v-model="createForm.category" style="width: 100%">
              <el-option v-for="item in categories" :key="item" :label="displayCategory(item)" :value="item" />
            </el-select>
          </div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>关联主体</label><el-input v-model="createForm.subject" placeholder="对象描述" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>问题描述</label><el-input v-model="createForm.detail" type="textarea" :rows="4" /></div>
          <div class="field"><label class="field__label">关联订单 ID</label><el-input v-model="createForm.order_id" placeholder="可选" /></div>
          <div class="field"><label class="field__label">关联任务 ID</label><el-input v-model="createForm.task_id" placeholder="可选" /></div>
          <div class="field"><label class="field__label">关联车辆 ID</label><el-input v-model="createForm.vehicle_id" placeholder="可选" /></div>
        </form>
      </template>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">登记</el-button>
      </template>
    </DetailDrawer>

    <DetailDrawer v-model="detailOpen" title="平台异常处置">
      <template #body>
        <template v-if="detail">
          <NoticeBar tone="info">管理员只能追加异常处理记录，不能改写运输订单、任务、打卡或费用记录。</NoticeBar>
          <dl class="kv section-gap">
            <dt>异常类型</dt><dd>{{ displayCategory(detail.exception.category) }}</dd>
            <dt>关联订单</dt><dd class="num">{{ detail.exception.order_id ? `订单 #${detail.exception.order_id}` : '—' }}</dd>
            <dt>上报人</dt><dd>{{ detail.exception.actor }}</dd>
            <dt>上报时间</dt><dd class="num">{{ stamp(detail.exception.created_at) }}</dd>
            <dt>问题描述</dt><dd>{{ detail.exception.detail }}</dd>
          </dl>
          <div class="field section-gap">
            <label class="field__label"><span class="field__req">*</span>处置结果</label>
            <el-select v-model="handlingForm.result" style="width: 100%">
              <el-option v-for="item in results" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>原因</label><el-input v-model="handlingForm.reason" type="textarea" :rows="3" /></div>
          <div class="field"><label class="field__label">补充说明</label><el-input v-model="handlingForm.detail" type="textarea" :rows="2" /></div>
          <div v-if="detail.handling_records.length" class="records">
            <h3 class="records-title">追加处理记录</h3>
            <ul class="record-list">
              <li v-for="record in detail.handling_records" :key="record.id">
                <StatusPill :text="record.result" />
                <span>{{ record.reason }}</span>
                <span class="record-meta">{{ record.actor }} · {{ stamp(record.handled_at) }}</span>
              </li>
            </ul>
          </div>
        </template>
      </template>
      <template #footer>
        <el-button @click="detailOpen = false">关闭</el-button>
        <el-button type="primary" :loading="saving" @click="submitHandling">提交处置</el-button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.drawer-form { padding-top: var(--space-4); }
.section-gap { margin-top: var(--space-4); }
.records { margin-top: var(--space-5); }
.records-title { margin: 0 0 var(--space-2); font-size: var(--font-size-sm); font-weight: 600; }
.record-list { margin: 0; padding: 0; list-style: none; }
.record-list li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3); padding: var(--space-2) 0; border-bottom: 1px solid var(--color-border); font-size: var(--font-size-sm); }
.record-list li:last-child { border-bottom: 0; }
.record-meta { color: var(--color-text-3); font-size: var(--font-size-xs); }
</style>
