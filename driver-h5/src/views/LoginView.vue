<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useAuthStore } from '@/stores/auth'

// 开发模式预填本地账号，生产构建留空由用户输入
const phone = ref(import.meta.env.DEV ? (import.meta.env.VITE_DEV_PHONE ?? '') : '')
const password = ref(import.meta.env.DEV ? (import.meta.env.VITE_DEV_PASSWORD ?? '') : '')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function onSubmit(): Promise<void> {
  loading.value = true
  try {
    await auth.login(phone.value, password.value)
    if (auth.role !== '司机') {
      showToast('该账号不是司机账号')
      return
    }
    const target = auth.blockedReason
      ? '/blocked'
      : auth.needsOnboarding
        ? '/onboarding'
        : '/home'
    await router.replace(target)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <h1 class="login-title">司机登录</h1>
    <form class="login-form" @submit.prevent="onSubmit">
      <van-field
        v-model="phone"
        label="手机号"
        placeholder="请输入手机号"
        autocomplete="username"
      />
      <van-field
        v-model="password"
        label="密码"
        type="password"
        placeholder="请输入密码"
        autocomplete="current-password"
      />
      <van-button
        class="submit"
        type="primary"
        native-type="submit"
        block
        :loading="loading"
      >
        登录
      </van-button>
    </form>
  </main>
</template>

<style scoped>
.login-page {
  padding: var(--space-6) var(--space-4);
}

.login-title {
  margin: var(--space-6) 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.login-form {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--space-2) var(--space-4);
}

.submit {
  margin: var(--space-6) 0;
  min-height: var(--tap-min);
}
</style>
