<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { registerCarrier } from '@/api/carrier'
import { useAuthStore } from '@/stores/auth'

const phone = ref('')
const password = ref('')
const loading = ref(false)
const showRegister = ref(false)
const regPhone = ref('')
const regPassword = ref('')
const regCompany = ref('')
const registering = ref(false)
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

async function onSubmit(): Promise<void> {
  loading.value = true
  try {
    await auth.login(phone.value, password.value)
    const redirect = route.query.redirect
    const dest = typeof redirect === 'string' ? redirect : homeFor(auth.role)
    await router.replace(dest)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}

async function onRegisterShipper(): Promise<void> {
  loading.value = true
  try {
    await auth.registerShipper(phone.value, password.value)
    await router.replace('/shipper')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '注册失败')
  } finally {
    loading.value = false
  }
}

async function onRegisterCarrier(): Promise<void> {
  registering.value = true
  try {
    await registerCarrier(regPhone.value, regPassword.value, regCompany.value)
    await auth.login(regPhone.value, regPassword.value)
    ElMessage.success('注册成功，请提交企业认证资料')
    await router.replace('/carrier/certification')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '注册失败')
  } finally {
    registering.value = false
  }
}

function homeFor(role: string | null): string {
  const map: Record<string, string> = {
    货主: '/shipper',
    物流公司: '/carrier',
    管理员: '/admin',
  }
  return map[role ?? ''] ?? '/login'
}
</script>

<template>
  <main class="login-page">
    <form class="login-card" @submit.prevent="onSubmit">
      <h1 class="login-title">物流运输管理平台</h1>
      <p class="login-subtitle">账号登录</p>
      <label class="field">
        <span class="field-label">手机号</span>
        <el-input v-model="phone" autocomplete="username" placeholder="请输入手机号" />
      </label>
      <label class="field">
        <span class="field-label">密码</span>
        <el-input
          v-model="password"
          type="password"
          autocomplete="current-password"
          placeholder="请输入密码"
          show-password
        />
      </label>
      <el-button class="submit" type="primary" native-type="submit" :loading="loading">
        登录
      </el-button>
      <el-button class="submit" type="button" :loading="loading" @click="onRegisterShipper">
        注册货主账号
      </el-button>
      <button class="switch" type="button" @click="showRegister = !showRegister">
        {{ showRegister ? '收起物流公司注册' : '物流公司注册' }}
      </button>

      <div v-if="showRegister" class="register">
        <p class="register-title">物流公司注册</p>
        <label class="field">
          <span class="field-label">手机号</span>
          <el-input v-model="regPhone" autocomplete="username" placeholder="请输入手机号" />
        </label>
        <label class="field">
          <span class="field-label">密码（至少 8 位）</span>
          <el-input
            v-model="regPassword"
            type="password"
            autocomplete="new-password"
            placeholder="请设置密码"
            show-password
          />
        </label>
        <label class="field">
          <span class="field-label">企业名称</span>
          <el-input v-model="regCompany" placeholder="请输入企业名称" />
        </label>
        <el-button class="submit" type="primary" :loading="registering" @click="onRegisterCarrier">
          注册并进入认证
        </el-button>
      </div>
    </form>
  </main>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

.login-card {
  width: 360px;
  padding: var(--space-8);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-light);
}

.login-title {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: 600;
}

.login-subtitle {
  margin: var(--space-1) 0 var(--space-6);
  color: var(--color-text-muted);
}

.field {
  display: block;
  margin-bottom: var(--space-4);
}

.field-label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.submit {
  width: 100%;
  margin-top: var(--space-2);
}

.switch {
  display: block;
  width: 100%;
  padding: var(--space-2) 0;
  margin-top: var(--space-2);
  font: inherit;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  background: transparent;
  border: 0;
  cursor: pointer;
}

.register {
  padding-top: var(--space-4);
  margin-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.register-title {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-md);
  font-weight: 600;
}
</style>
