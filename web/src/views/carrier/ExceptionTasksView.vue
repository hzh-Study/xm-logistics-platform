<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listTasks } from '@/api/dispatch'
import type { TransportTask } from '@/types/dispatch'

const router = useRouter()
const tasks = ref<TransportTask[]>([])
const loading = ref(false)

// 仅列出承运中的任务，已终结任务无需进入异常处理
const activeStatuses = ['待装货', '运输中', '待签收', '待确认完成', '异常']

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    const all = await listTasks()
    tasks.value = all.filter((task) => activeStatuses.includes(task.status))
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取运输任务失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="exception-tasks" v-loading="loading">
    <h1>运输异常</h1>
    <p class="muted">选择运输任务，查看在途异常并追加处理记录。换车换司机必须在此处理，不覆盖已有打卡与照片。</p>
    <el-table :data="tasks" size="small" empty-text="暂无承运中的运输任务">
      <el-table-column prop="task_no" label="任务号" min-width="170" />
      <el-table-column prop="order_no" label="订单号" min-width="170" />
      <el-table-column prop="driver_name" label="司机" width="110" />
      <el-table-column prop="vehicle_plate" label="车牌" width="120" />
      <el-table-column prop="status" label="任务状态" width="120" />
      <el-table-column label="操作" width="120">
        <template #default="scope">
          <el-button link type="primary" @click="router.push(`/carrier/tasks/${scope.row.id}/exceptions`)">
            处理异常
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.exception-tasks h1 { margin: 0 0 var(--space-2); font-size: var(--font-size-xl); }
.muted { margin: 0 0 var(--space-4); color: var(--color-text-muted); font-size: var(--font-size-sm); }
</style>
