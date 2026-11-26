<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import H5PageHeader from '@/components/H5PageHeader.vue'
import H5Card from '@/components/H5Card.vue'
import H5Notice from '@/components/H5Notice.vue'
import H5BottomBar from '@/components/H5BottomBar.vue'

const auth = useAuthStore()
const router = useRouter()

async function onLogout(): Promise<void> {
  await auth.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="h5-page h5-page--with-bar">
    <H5PageHeader title="账号不可用" :show-back="false" />
    <main class="h5-scroll">
      <div class="blocked-hero">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M5 5l14 14" />
        </svg>
        <h2>账号暂不可用</h2>
      </div>

      <H5Card>
        <H5Notice tone="error">
          账号状态：{{ auth.user?.account_status ?? '已禁用' }}<br />
          阻断原因：{{ auth.blockedReason || '所属物流公司账号异常，已暂停司机端业务。' }}
        </H5Notice>
        <p class="blocked-hint">请联系所属物流公司处理，历史任务与报销记录均予保留。</p>
      </H5Card>

      <H5Card>
        <h3 class="blocked-title">其他阻断情形</h3>
        <div class="h5-row"><span class="k">账号状态</span><span class="v">已禁用 / 已注销</span></div>
        <div class="h5-row"><span class="k">雇佣关系</span><span class="v">离职</span></div>
        <div class="h5-row"><span class="k">所属公司</span><span class="v">已禁用</span></div>
        <p class="blocked-hint">以上任一情形均会阻断运输业务，页面只读且无可执行操作。</p>
      </H5Card>
    </main>
    <H5BottomBar>
      <van-button block type="primary" @click="onLogout">退出登录</van-button>
    </H5BottomBar>
  </div>
</template>

<style scoped>
.blocked-hero { text-align: center; padding: var(--space-10) var(--space-4) var(--space-6); }
.blocked-hero svg { width: 40px; height: 40px; fill: none; stroke: var(--color-text-3); stroke-width: 1.2; }
.blocked-hero h2 { margin: var(--space-4) 0 0; font-size: var(--font-size-md); }
.blocked-hint { margin: var(--space-3) 0 0; font-size: var(--font-size-sm); color: var(--color-text-3); }
.blocked-title { margin: 0 0 var(--space-2); font-size: var(--font-size-sm); font-weight: 600; }
</style>
