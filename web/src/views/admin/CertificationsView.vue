<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import PageHeader from '@/components/PageHeader.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import DetailDrawer from '@/components/DetailDrawer.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { CertCategory, CertItem, ReviewDecision } from '@/types/admin'

const rows = ref<CertItem[]>([])
const loading = ref(false)
const saving = ref(false)
const filter = reactive({ category: '' as CertCategory | '', status: '' })
const reviewOpen = ref(false)
const current = ref<CertItem | null>(null)
const decision = ref<ReviewDecision>('审核通过')
const reason = ref('')
const reasonError = ref('')

const categories: CertCategory[] = ['货主', '企业', '司机', '驾驶资格', '车辆证件']
const title = computed(() => (current.value ? `审核 ${current.value.category} 认证 · ${current.value.subject_name}` : '审核认证'))

function stamp(value: string | null): string {
  return value ? value.replace('T', ' ').slice(0, 16) : '—'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    rows.value = await adminApi.fetchCertifications({
      category: filter.category || undefined,
      status: filter.status || undefined,
    })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载认证列表失败')
  } finally {
    loading.value = false
  }
}

function reset(): void {
  filter.category = ''
  filter.status = ''
  void load()
}

function openReview(item: CertItem): void {
  current.value = item
  decision.value = '审核通过'
  reason.value = ''
  reasonError.value = ''
  reviewOpen.value = true
}

async function submitReview(): Promise<void> {
  if (!current.value) return
  if (decision.value === '审核不通过' && !reason.value.trim()) {
    reasonError.value = '驳回原因为必填项，请说明驳回理由。'
    return
  }
  saving.value = true
  try {
    await adminApi.reviewCertificationUnified({
      category: current.value.category,
      target_id: current.value.id,
      decision: decision.value,
      reason: reason.value,
    })
    ElMessage.success('审核已提交')
    reviewOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交审核失败')
  } finally {
    saving.value = false
  }
}

async function changeAccountStatus(item: CertItem, status: '正常使用' | '已禁用'): Promise<void> {
  try {
    await adminApi.setAccountStatus(item.subject_id, status)
    ElMessage.success(status === '已禁用' ? '账号已禁用' : '账号已恢复')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '账号处置失败')
  }
}

onMounted(load)
</script>

<template>
  <section>
    <PageHeader title="统一认证审核" subtitle="集中审核货主、物流公司、司机、驾驶资格与车辆证件 · 驳回原因必填" />

    <FilterPanel>
      <div class="filter-grid">
        <div class="field">
          <label class="field__label" for="cert-cat">主体类型</label>
          <el-select id="cert-cat" v-model="filter.category" placeholder="全部" clearable>
            <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="field">
          <label class="field__label" for="cert-status">认证状态</label>
          <el-select id="cert-status" v-model="filter.status" placeholder="全部" clearable>
            <el-option v-for="item in ['未提交', '待审核', '审核通过', '审核不通过']" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
      </div>
      <div class="filter-actions">
        <el-button @click="reset">重置</el-button>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </FilterPanel>

    <section class="panel">
      <div class="panel-head"><span class="panel-title">审核列表</span></div>
      <div class="panel-body panel-body--tight">
        <EmptyState v-if="!rows.length" text="暂无待审核的认证资料" />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th class="num">主体编号</th><th>主体名称</th><th>主体类型</th><th class="num">提交时间</th><th>认证状态</th><th class="ops">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id">
                <td class="num">{{ row.subject_id }}</td>
                <td>{{ row.subject_name }}</td>
                <td>{{ row.category }}</td>
                <td class="num">{{ stamp(row.submitted_at) }}</td>
                <td><StatusPill :text="row.auth_status" /></td>
                <td class="ops">
                  <el-button type="primary" link @click="openReview(row)">{{ row.auth_status === '待审核' ? '审核' : '查看' }}</el-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="pagination"><span>共 {{ rows.length }} 条</span></div>
        </div>
      </div>
    </section>

    <DetailDrawer v-model="reviewOpen" :title="title">
      <template #body>
        <template v-if="current">
          <NoticeBar tone="info">审核通过后资料生效；驳回必须填写原因，原因作为追加记录对该主体可见。</NoticeBar>
          <dl class="kv section-gap">
            <dt>主体名称</dt><dd>{{ current.subject_name }}</dd>
            <dt>主体类型</dt><dd>{{ current.category }}</dd>
            <dt>账号状态</dt><dd><StatusPill :text="current.account_status" /></dd>
            <dt>提交时间</dt><dd class="num">{{ stamp(current.submitted_at) }}</dd>
            <dt>资料摘要</dt><dd>{{ current.detail }}</dd>
            <dt v-if="current.reason">驳回原因</dt><dd v-if="current.reason">{{ current.reason }}</dd>
          </dl>
          <div v-if="current.category !== '车辆证件'" class="account-ops">
            <el-button v-if="current.account_status === '正常使用'" @click="changeAccountStatus(current, '已禁用')">禁用账号</el-button>
            <el-button v-else @click="changeAccountStatus(current, '正常使用')">恢复账号</el-button>
          </div>
          <div class="field section-gap">
            <label class="field__label" for="cert-reason"><span v-if="decision === '审核不通过'" class="field__req">*</span>驳回原因（驳回时必填）</label>
            <el-input id="cert-reason" v-model="reason" type="textarea" :rows="3" placeholder="请填写驳回原因，主体可见" />
            <p v-if="reasonError" class="field__error">{{ reasonError }}</p>
          </div>
        </template>
      </template>
      <template #footer>
        <el-button @click="reviewOpen = false">关闭</el-button>
        <el-button type="danger" @click="decision = '审核不通过'">驳回</el-button>
        <el-button type="primary" :loading="saving" @click="submitReview">通过</el-button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.section-gap { margin-top: var(--space-4); }
.account-ops { display: flex; gap: var(--space-2); }
</style>
