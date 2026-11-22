<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import type { Announcement, PlatformNotice } from '@/types/admin'

const kind = ref<'公告' | '通知'>('公告')
const loading = ref(false)
const form = reactive({ title: '', body: '', scope: '全部' })
const announcements = ref<Announcement[]>([])
const notices = ref<PlatformNotice[]>([])

const scopes = ['全部', '货主', '物流公司', '司机']

async function load(): Promise<void> {
  loading.value = true
  try {
    const [a, n] = await Promise.all([
      adminApi.fetchAnnouncements(),
      adminApi.fetchNotices(),
    ])
    announcements.value = a
    notices.value = n
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载平台内容失败')
  } finally {
    loading.value = false
  }
}

async function publish(): Promise<void> {
  if (!form.title.trim() || !form.body.trim()) {
    ElMessage.warning('标题与正文必填')
    return
  }
  try {
    if (kind.value === '公告') {
      await adminApi.publishAnnouncement({ ...form })
    } else {
      await adminApi.publishNotice({ ...form })
    }
    ElMessage.success(kind.value === '公告' ? '公告已发布' : '通知已发布')
    form.title = ''
    form.body = ''
    form.scope = '全部'
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '发布失败')
  }
}

onMounted(load)
</script>

<template>
  <section class="announcements">
    <h1 class="page-title">平台公告与通知</h1>
    <p class="page-note">公告与通知为独立内容通道，不进入业务站内通知。</p>

    <div class="panel">
      <el-radio-group v-model="kind">
        <el-radio-button value="公告">发布公告</el-radio-button>
        <el-radio-button value="通知">发布通知</el-radio-button>
      </el-radio-group>
      <el-form label-position="top" class="form">
        <el-form-item label="标题">
          <el-input v-model="form.title" maxlength="200" placeholder="输入标题" />
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="form.body" type="textarea" :rows="3" maxlength="5000" placeholder="输入正文" />
        </el-form-item>
        <el-form-item label="可见范围">
          <el-select v-model="form.scope" class="field">
            <el-option v-for="scope in scopes" :key="scope" :label="scope" :value="scope" />
          </el-select>
        </el-form-item>
        <el-button type="primary" @click="publish">发布</el-button>
      </el-form>
    </div>

    <h2 class="section-title">已发布内容</h2>
    <el-table :data="kind === '公告' ? announcements : notices" v-loading="loading" row-key="id">
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="scope" label="可见范围" width="110" />
      <el-table-column prop="channel" label="内容通道" width="110" />
      <el-table-column prop="published_at" label="发布时间" width="200" />
      <el-table-column label="正文">
        <template #default="{ row }">{{ row.body }}</template>
      </el-table-column>
      <template #empty><span>暂无已发布内容。</span></template>
    </el-table>
  </section>
</template>

<style scoped>
.announcements {
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

.panel {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.form {
  margin-top: var(--space-4);
  max-width: 520px;
}

.field {
  width: 200px;
}

.section-title {
  margin: var(--space-6) 0 var(--space-3);
  font-size: var(--font-size-md);
  font-weight: 600;
}
</style>
