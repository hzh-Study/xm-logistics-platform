<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import H5PageHeader from '@/components/H5PageHeader.vue'

const phone = ref(import.meta.env.DEV ? (import.meta.env.VITE_DEV_PHONE ?? '') : '')
const password = ref(import.meta.env.DEV ? (import.meta.env.VITE_DEV_PASSWORD ?? '') : '')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function onSubmit(): Promise<void> {
  if (!phone.value.trim() || !password.value) {
    showToast('请填写手机号与密码')
    return
  }
  loading.value = true
  try {
    await auth.login(phone.value, password.value)
    if (auth.role !== '司机') {
      showToast('该账号不是司机账号')
      return
    }
    await router.replace(auth.blockedReason ? '/blocked' : auth.needsOnboarding ? '/onboarding' : '/home')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="h5-page">
    <H5PageHeader title="司机登录" :show-back="false" />
    <main class="h5-scroll login-body">
      <div class="login-intro">
        <div class="login-mark">运</div>
        <h1>司机登录</h1>
        <p>使用物流公司分配的账号登录</p>
      </div>

      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field v-model="phone" label="手机号" placeholder="请输入手机号" autocomplete="username" />
          <van-field v-model="password" label="密码" type="password" placeholder="请输入密码" autocomplete="current-password" />
        </van-cell-group>
        <div class="login-tips">
          <p>首次登录将强制修改临时密码并完成身份绑定。</p>
          <p>司机账号由物流公司创建，不支持自行注册，也无法承接公共货源。</p>
        </div>
        <div class="login-submit">
          <van-button block type="primary" native-type="submit" :loading="loading">登录</van-button>
        </div>
      </van-form>
    </main>
  </div>
</template>

<style scoped>
.login-body { padding-top: var(--space-8); }
.login-intro { text-align: center; margin-bottom: var(--space-8); }
.login-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  margin: 0 auto var(--space-3);
  border-radius: var(--radius-card);
  background: var(--color-accent);
  color: var(--color-surface);
  font-size: var(--font-size-lg);
  font-weight: 600;
}
.login-intro h1 { margin: 0; font-size: var(--font-size-xl); font-weight: 600; }
.login-intro p { margin: var(--space-1) 0 0; font-size: var(--font-size-sm); color: var(--color-text-3); }
.login-tips { margin: var(--space-6) var(--space-4) 0; font-size: var(--font-size-xs); color: var(--color-text-3); line-height: 1.6; }
.login-tips p { margin: 0 0 var(--space-1); }
.login-submit { margin: var(--space-6) var(--space-4) 0; }
</style>
