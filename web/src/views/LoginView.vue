<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { registerCarrier } from '@/api/carrier'
import { useAuthStore } from '@/stores/auth'

type RegisterRole = '货主' | '物流公司'

const phone = ref(import.meta.env.DEV ? (import.meta.env.VITE_DEV_PHONE ?? '') : '')
const password = ref(import.meta.env.DEV ? (import.meta.env.VITE_DEV_PASSWORD ?? '') : '')
const loading = ref(false)
const showRegister = ref(false)
const registerRole = ref<RegisterRole>('货主')
const regPhone = ref('')
const regPassword = ref('')
const regCompany = ref('')
const registering = ref(false)

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const registerValid = computed(() =>
  regPhone.value.trim().length > 0 &&
  regPassword.value.length >= 8 &&
  (registerRole.value === '货主' || regCompany.value.trim().length > 0),
)

async function onSubmit(): Promise<void> {
  loading.value = true
  try {
    await auth.login(phone.value, password.value)
    const redirect = route.query.redirect
    await router.replace(typeof redirect === 'string' ? redirect : homeFor(auth.role))
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}

async function onRegister(): Promise<void> {
  if (!regPhone.value.trim()) {
    ElMessage.warning('请填写手机号')
    return
  }
  if (regPassword.value.length < 8) {
    ElMessage.warning('密码不少于 8 位，请使用字母与数字组合')
    return
  }
  if (registerRole.value === '物流公司' && !regCompany.value.trim()) {
    ElMessage.warning('请填写企业名称')
    return
  }
  registering.value = true
  try {
    if (registerRole.value === '货主') {
      await auth.registerShipper(regPhone.value, regPassword.value)
      await router.replace('/shipper')
    } else {
      await registerCarrier(regPhone.value, regPassword.value, regCompany.value)
      await auth.login(regPhone.value, regPassword.value)
      ElMessage.success('注册成功，请提交企业认证资料')
      await router.replace('/carrier/certification')
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '注册失败')
  } finally {
    registering.value = false
  }
}

function homeFor(role: string | null): string {
  const map: Record<string, string> = { 货主: '/shipper', 物流公司: '/carrier', 管理员: '/admin' }
  return map[role ?? ''] ?? '/login'
}
</script>

<template>
  <main class="login-page">
    <section class="login-card">
      <div class="login-logo">
        <span class="login-logo__mark">运</span>
        <span>物流运输管理平台</span>
      </div>
      <h1 class="login-title">账号登录</h1>
      <p class="login-sub">使用平台分配的账号登录</p>

      <form @submit.prevent="onSubmit">
        <div class="field">
          <label class="field__label" for="login-phone"><span class="field__req">*</span>手机号</label>
          <el-input id="login-phone" v-model="phone" placeholder="请输入手机号" autocomplete="username" />
        </div>
        <div class="field">
          <label class="field__label" for="login-password"><span class="field__req">*</span>密码</label>
          <el-input
            id="login-password"
            v-model="password"
            type="password"
            show-password
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </div>
        <el-button class="login-submit" type="primary" native-type="submit" :loading="loading">登录</el-button>
      </form>

      <div class="login-foot">
        <el-button type="primary" link @click="showRegister = !showRegister">
          {{ showRegister ? '收起注册' : '注册新账号' }}
        </el-button>
      </div>

      <div v-if="showRegister" class="register-zone">
        <p class="register-hint">选择主体类型后填写资料，注册通过后进入对应工作台。</p>
        <div class="field">
          <span class="field__label"><span class="field__req">*</span>主体类型</span>
          <el-radio-group v-model="registerRole">
            <el-radio value="货主">货主</el-radio>
            <el-radio value="物流公司">物流公司</el-radio>
          </el-radio-group>
        </div>
        <div class="field">
          <label class="field__label" for="reg-phone"><span class="field__req">*</span>手机号</label>
          <el-input id="reg-phone" v-model="regPhone" placeholder="请输入手机号" />
        </div>
        <div class="field">
          <label class="field__label" for="reg-password"><span class="field__req">*</span>密码</label>
          <el-input id="reg-password" v-model="regPassword" type="password" show-password placeholder="请输入密码" />
          <p class="field__help">密码不少于 8 位，建议使用字母与数字组合。</p>
        </div>
        <div v-if="registerRole === '物流公司'" class="field">
          <label class="field__label" for="reg-company"><span class="field__req">*</span>企业名称</label>
          <el-input id="reg-company" v-model="regCompany" placeholder="请输入企业名称" />
        </div>
        <el-button class="login-submit" type="primary" :disabled="!registerValid" :loading="registering" @click="onRegister">
          注册并进入
        </el-button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; background: var(--color-bg); padding: var(--space-6); }
.login-card {
  width: 400px;
  max-width: 100%;
  padding: var(--space-8);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}
.login-logo { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-6); font-weight: 600; }
.login-logo__mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-control);
  background: var(--color-accent);
  color: var(--color-surface);
  font-size: var(--font-size-md);
}
.login-title { margin: 0; font-size: var(--font-size-xl); font-weight: 600; letter-spacing: -0.3px; }
.login-sub { margin: var(--space-1) 0 var(--space-6); font-size: var(--font-size-sm); color: var(--color-text-3); }
.login-submit { width: 100%; }
.login-foot { margin-top: var(--space-4); text-align: center; }
.register-zone { margin-top: var(--space-5); padding-top: var(--space-5); border-top: 1px solid var(--color-border); }
.register-hint {
  margin: 0 0 var(--space-4);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-control);
  background: var(--color-fill);
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
}
</style>
