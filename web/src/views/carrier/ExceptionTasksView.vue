<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listTasks } from '@/api/dispatch'
import { getCarrierExceptions } from '@/api/exception'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import PhotoGrid from '@/components/PhotoGrid.vue'
import type { Anomaly } from '@/types/exception'
import type { TransportTask } from '@/types/dispatch'

interface ExceptionRow {
  anomaly: Anomaly
  task: TransportTask
}

const router = useRouter()
const rows = ref<ExceptionRow[]>([])
const loading = ref(false)
const kindFilter = ref('')
const actorFilter = ref('')
const taskFilter = ref('')
const detailOpen = ref(false)
const current = ref<ExceptionRow | null>(null)

const activeStatuses = ['待装货', '运输中', '待签收', '待确认完成', '异常']

const filtered = computed(() => rows.value.filter((row) => {
  const kind = kindFilter.value && displayKind(row.anomaly.kind).includes(kindFilter.value)
  const actor = actorFilter.value && row.anomaly.actor.includes(actorFilter.value)
  const task = taskFilter.value && row.anomaly.task_no.includes(taskFilter.value)
  return (!kindFilter.value || kind) && (!actorFilter.value || actor) && (!taskFilter.value || task)
}))

function displayKind(kind: string): string {
  const map: Record<string, string> = { 故障: '车辆故障', 货物异常: '货物问题', 其他: '其它' }
  return map[kind] ?? kind
}

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const all = await listTasks()
    const active = all.filter((task) => activeStatuses.includes(task.status))
    const results = await Promise.all(active.map((task) => getCarrierExceptions(task.id)))
    rows.value = results.flatMap((view, index) =>
      view.anomalies.map((anomaly) => ({ anomaly, task: active[index] })),
    )
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取异常记录失败')
  } finally {
    loading.value = false
  }
}

function openDetail(row: ExceptionRow): void {
  current.value = row
  detailOpen.value = true
}

function handle(row: ExceptionRow): void {
  router.push(`/carrier/tasks/${row.task.id}/exceptions`)
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="运输异常" :subtitle="`待处置 ${rows.filter((row) => !row.anomaly.started).length} · 本月异常 ${rows.length} 条`" />

    <FilterPanel>
      <div class="filter-grid">
        <div class="field">
          <label class="field__label" for="exc-kind">异常类型</label>
          <el-select id="exc-kind" v-model="kindFilter" placeholder="全部" clearable>
            <el-option v-for="item in ['车辆故障', '事故', '封路', '拥堵', '货物问题', '预计延误', '位置异常', '其它']" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field"><label class="field__label" for="exc-actor">上报人</label><el-input id="exc-actor" v-model="actorFilter" placeholder="请输入上报人" clearable /></div>
        <div class="field"><label class="field__label" for="exc-task">运输任务</label><el-input id="exc-task" v-model="taskFilter" placeholder="请输入任务编号" clearable /></div>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">异常列表</span><span class="panel-hint">异常上报与处置 · 结果追加为异常处理记录，不覆盖原始记录</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!filtered.length" text="暂无运输异常" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">异常编号</th><th>异常类型 / 任务</th><th>上报人</th><th class="num">上报时间</th><th>现场照片</th><th>处理结果</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in filtered" :key="row.anomaly.id">
                <td class="num">{{ row.anomaly.anomaly_no }}</td>
                <td>{{ displayKind(row.anomaly.kind) }}<div class="cell-sub">{{ row.anomaly.task_no }}</div></td>
                <td>{{ row.anomaly.actor }}</td>
                <td class="num">{{ stamp(row.anomaly.occurred_at) }}</td>
                <td>{{ row.anomaly.photos.length }} 张</td>
                <td>{{ row.anomaly.started ? '已处置' : '—' }}</td>
                <td class="ops">
                  <el-button v-if="!row.anomaly.started" type="primary" link @click="handle(row)">处置</el-button>
                  <el-button type="primary" link @click="openDetail(row)">查看详情</el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ filtered.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="detailOpen" title="异常详情">
      <template #body>
        <template v-if="current">
          <dl class="kv">
            <dt>异常编号</dt><dd class="num">{{ current.anomaly.anomaly_no }}</dd>
            <dt>异常类型</dt><dd><StatusPill :text="displayKind(current.anomaly.kind)" /></dd>
            <dt>上报人</dt><dd>{{ current.anomaly.actor }}</dd>
            <dt>上报时间</dt><dd class="num">{{ stamp(current.anomaly.occurred_at) }}</dd>
            <dt>关联任务</dt><dd class="num">{{ current.anomaly.task_no }}</dd>
            <dt>异常说明</dt><dd>{{ current.anomaly.detail }}</dd>
          </dl>
          <PhotoGrid v-if="current.anomaly.photos.length" :photos="current.anomaly.photos" />
        </template>
      </template>
    </DetailDrawer>
  </section>
</template>
