<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { Announcement, PlatformNotice } from '@/types/admin'

const kind = ref<'公告' | '通知'>('公告')
const loading = ref(false)
const saving = ref(false)
const createOpen = ref(false)
const keyword = ref('')
const form = reactive({ title: '', body: '', scope: '全部' })
const announcements = ref<Announcement[]>([])
const notices = ref<PlatformNotice[]>([])
const detailOpen = ref(false)
const detailText = ref('')
const detailTitle = ref('')
const scopes = ['全部', '货主', '物流公司', '司机']

function stamp(value: string): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

const rows = () => (kind.value === '公告' ? announcements.value : notices.value).filter((item) =>
  !keyword.value || item.title.includes(keyword.value),
)

async function load(): Promise<void> {
  loading.value = true
  try {
    const [a, n] = await Promise.all([adminApi.fetchAnnouncements(), adminApi.fetchNotices()])
    announcements.value = a
    notices.value = n
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载平台内容失败')
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  form.title = ''
  form.body = ''
  form.scope = '全部'
  createOpen.value = true
}

async function publish(): Promise<void> {
  if (!form.title.trim() || !form.body.trim()) {
    ElMessage.warning('标题与正文必填')
    return
  }
  saving.value = true
  try {
    if (kind.value === '公告') await adminApi.publishAnnouncement({ ...form })
    else await adminApi.publishNotice({ ...form })
    ElMessage.success(kind.value === '公告' ? '公告已发布' : '通知已发布')
    createOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '发布失败')
  } finally {
    saving.value = false
  }
}

function openDetail(title: string, body: string): void {
  detailTitle.value = title
  detailText.value = body
  detailOpen.value = true
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="平台公告与通知" subtitle="公告为独立内容，与业务事件触发的通知分开管理">
      <template #actions><el-button type="primary" @click="openCreate">发布{{ kind }}</el-button></template>
    </PageHeader>

    <div class="tabs">
      <button class="tab" :class="{ 'tab--active': kind === '公告' }" type="button" @click="kind = '公告'">公告</button>
      <button class="tab" :class="{ 'tab--active': kind === '通知' }" type="button" @click="kind = '通知'">通知</button>
    </div>

    <FilterPanel>
      <div class="filter-grid">
        <div class="field"><label class="field__label" for="an-kw">标题</label><el-input id="an-kw" v-model="keyword" placeholder="请输入标题关键词" clearable /></div>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">{{ kind }}列表</span><span class="panel-hint">共 {{ rows().length }} 条</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!rows().length" :text="`暂无${kind}`" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th>标题</th><th>接收范围</th><th class="num">发布时间</th><th>通道</th><th class="ops">操作</th></tr></thead>
            <tbody>
              <tr v-for="row in rows()" :key="row.id">
                <td>{{ row.title }}</td>
                <td>{{ row.scope }}</td>
                <td class="num">{{ stamp(row.published_at) }}</td>
                <td>{{ row.channel }}</td>
                <td class="ops"><el-button type="primary" link @click="openDetail(row.title, row.body)">查看</el-button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="createOpen" :title="`发布${kind}`">
      <template #body>
        <NoticeBar tone="info">公告按接收范围发布；发布后即对所有匹配角色可见。</NoticeBar>
        <form class="drawer-form">
          <div class="field"><label class="field__label"><span class="field__req">*</span>标题</label><el-input v-model="form.title" placeholder="请输入标题" /></div>
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>接收范围</label>
            <el-select v-model="form.scope" style="width: 100%">
              <el-option v-for="item in scopes" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>正文</label><el-input v-model="form.body" type="textarea" :rows="8" placeholder="请输入正文" /></div>
        </form>
      </template>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="publish">发布</el-button>
      </template>
    </DetailDrawer>

    <DetailDrawer v-model="detailOpen" :title="detailTitle">
      <template #body><div class="article">{{ detailText }}</div></template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.tabs { display: flex; gap: var(--space-6); border-bottom: 1px solid var(--color-border); margin-bottom: var(--space-4); }
.tab { padding: var(--space-3) 0; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--color-text-2); font-size: var(--font-size-md); cursor: pointer; margin-bottom: -1px; }
.tab--active { color: var(--color-accent); border-bottom-color: var(--color-accent); font-weight: 500; }
.drawer-form { padding-top: var(--space-4); }
.article { white-space: pre-wrap; line-height: 1.7; color: var(--color-text-2); }
</style>
