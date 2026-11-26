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
import type { TaskStatus, TransportTask } from '@/types/dispatch'

const rows = ref<TransportTask[]>([])
const loading = ref(false)
const detail = ref<TransportTask | null>(null)
const detailOpen = ref(false)
const filter = reactive({ status: '' as TaskStatus | '', order_id: undefined as number | undefined, task_no: '' })
const statuses: TaskStatus[] = ['待司机确认', '待装货', '运输中', '待签收', '待确认完成', '已完成', '异常', '已拒绝']

function stamp(value: string | null): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await adminApi.fetchPlatformTasks({ ...filter })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载任务失败')
  } finally {
    loading.value = false
  }
}

function reset(): void {
  filter.status = ''
  filter.order_id = undefined
  filter.task_no = ''
  void load()
}

async function openDetail(task: TransportTask): Promise<void> {
  try {
    detail.value = await adminApi.fetchPlatformTask(task.id)
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取任务详情失败')
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="运输任务查询" subtitle="平台级只读查询 · 可查阅业务证据链" />

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="at-no">任务编号</label><el-input id="at-no" v-model="filter.task_no" placeholder="请输入任务编号" clearable /></div>
        <div class="field"><label class="field__label" for="at-order">订单 ID</label><el-input id="at-order" v-model="filter.order_id" placeholder="请输入订单 ID" clearable /></div>
        <div class="field">
          <label class="field__label" for="at-status">任务状态</label>
          <el-select id="at-status" v-model="filter.status" placeholder="全部" clearable>
            <el-option v-for="item in statuses" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
      </div>
      <div class="filter-actions">
        <el-button @click="reset">重置</el-button>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">任务列表</span><span class="panel-hint">管理员只读 · 不提供改写业务记录的按钮</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!rows.length" text="暂无运输任务" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">任务编号</th><th>物流公司 / 司机</th><th>车辆</th><th>关联订单</th><th>任务状态</th><th class="num">计划送达</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id">
                <td class="num">{{ row.task_no }}</td>
                <td>公司 #{{ row.carrier_id }} / {{ row.driver_name }}</td>
                <td class="num">{{ row.vehicle_plate }}</td>
                <td class="num">{{ row.order_no }}</td>
                <td><StatusPill :text="row.status" /></td>
                <td class="num">{{ stamp(row.planned_deliver_at) }}</td>
                <td class="ops"><el-button type="primary" link @click="openDetail(row)">查看</el-button></td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ rows.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="detailOpen" title="运输任务详情">
      <template #body>
        <NoticeBar v-if="detail" tone="info">管理员只读查看，打卡照片与费用凭证可查阅但不能修改。</NoticeBar>
        <dl v-if="detail" class="kv section-gap">
          <dt>任务编号</dt><dd class="num">{{ detail.task_no }}</dd>
          <dt>任务状态</dt><dd><StatusPill :text="detail.status" /></dd>
          <dt>关联订单</dt><dd class="num">{{ detail.order_no }}</dd>
          <dt>司机 / 车辆</dt><dd>{{ detail.driver_name }} / {{ detail.vehicle_plate }}</dd>
          <dt>计划装货</dt><dd class="num">{{ stamp(detail.planned_load_at) }}</dd>
          <dt>计划送达</dt><dd class="num">{{ stamp(detail.planned_deliver_at) }}</dd>
          <dt>接单时间</dt><dd class="num">{{ stamp(detail.accepted_at) }}</dd>
          <dt>拒绝原因</dt><dd>{{ detail.reject_reason || '—' }}</dd>
          <dt>派单备注</dt><dd>{{ detail.notes || '—' }}</dd>
        </dl>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.section-gap { margin-top: var(--space-4); }
</style>
