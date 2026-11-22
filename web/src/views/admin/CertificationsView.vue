<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import type { CertCategory, CertItem, ReviewDecision } from '@/types/admin'

const rows = ref<CertItem[]>([])
const loading = ref(false)
const filter = reactive({ category: '' as CertCategory | '', status: '' })
const reviewVisible = ref(false)
const current = ref<CertItem | null>(null)
const decision = ref<ReviewDecision>('审核通过')
const reason = ref('')

const categories: CertCategory[] = ['货主', '企业', '司机', '驾驶资格', '车辆证件']
const canManageAccount = (item: CertItem): boolean => item.category !== '车辆证件'
const title = computed(() =>
  current.value ? `审核 ${current.value.category} 认证 · ${current.value.subject_name}` : '审核认证',
)

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

function openReview(item: CertItem): void {
  current.value = item
  decision.value = '审核通过'
  reason.value = ''
  reviewVisible.value = true
}

async function submitReview(): Promise<void> {
  if (!current.value) return
  if (decision.value === '审核不通过' && !reason.value.trim()) {
    ElMessage.warning('驳回原因必填')
    return
  }
  try {
    await adminApi.reviewCertificationUnified({
      category: current.value.category,
      target_id: current.value.id,
      decision: decision.value,
      reason: reason.value,
    })
    ElMessage.success('审核已提交')
    reviewVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交审核失败')
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
  <section class="certs">
    <h1 class="page-title">统一认证审核</h1>
    <p class="page-note">覆盖货主、企业、司机、驾驶资格与车辆证件；驳回必须填写原因。</p>

    <div class="toolbar">
      <el-select v-model="filter.category" class="field" placeholder="全部类别" clearable>
        <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
      </el-select>
      <el-input v-model="filter.status" class="field" placeholder="当前状态" clearable />
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" row-key="id">
      <el-table-column prop="category" label="认证类别" width="110" />
      <el-table-column prop="subject_name" label="主体" />
      <el-table-column prop="auth_status" label="当前状态" width="110" />
      <el-table-column label="账号状态" width="110">
        <template #default="{ row }">
          <span v-if="canManageAccount(row)">{{ row.account_status }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="detail" label="资料摘要" />
      <el-table-column label="驳回原因">
        <template #default="{ row }">{{ row.reason || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button type="primary" link @click="openReview(row)">审核</el-button>
          <template v-if="canManageAccount(row)">
            <el-button
              v-if="row.account_status === '正常使用'"
              type="warning"
              link
              @click="changeAccountStatus(row, '已禁用')"
            >
              禁用
            </el-button>
            <el-button v-else type="success" link @click="changeAccountStatus(row, '正常使用')">
              恢复
            </el-button>
          </template>
        </template>
      </el-table-column>
      <template #empty><span>暂无认证记录。</span></template>
    </el-table>

    <el-dialog v-model="reviewVisible" :title="title" width="480px">
      <el-form label-position="top">
        <el-form-item label="审核结论">
          <el-radio-group v-model="decision">
            <el-radio value="审核通过">审核通过</el-radio>
            <el-radio value="审核不通过">审核不通过</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="驳回原因" :required="decision === '审核不通过'">
          <el-input
            v-model="reason"
            type="textarea"
            :rows="3"
            maxlength="1000"
            :placeholder="decision === '审核不通过' ? '请填写驳回原因，驳回原因必填' : '可选填审核说明'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReview">提交审核</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.certs {
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
  width: 180px;
}
</style>
