<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { changePassword, completeBinding } from '@/api/driver'
import { useAuthStore } from '@/stores/auth'
import type { DriverBindingPayload } from '@/types/driver'

const auth = useAuthStore()
const router = useRouter()
const saving = ref(false)
const step = computed(() => (auth.onboarding?.must_change_password ? 1 : 2))

const passwordForm = reactive({ password: '', confirm: '' })
const bindingForm = reactive<DriverBindingPayload>({
  name: '',
  id_number: '',
  license_no: '',
  license_type: '',
  license_expiry: '',
})

function fail(error: unknown, fallback: string): void {
  showToast(error instanceof Error ? error.message : fallback)
}

async function onSubmitPassword(): Promise<void> {
  if (passwordForm.password !== passwordForm.confirm) {
    showToast('两次输入的新密码不一致')
    return
  }
  saving.value = true
  try {
    await changePassword(passwordForm.password)
    await auth.refreshOnboarding()
    showToast('密码已修改，请补全身份与驾驶证资料')
  } catch (error) {
    fail(error, '修改密码失败')
  } finally {
    saving.value = false
  }
}

async function onSubmitBinding(): Promise<void> {
  saving.value = true
  try {
    await completeBinding({ ...bindingForm })
    await auth.refreshOnboarding()
    showToast('身份绑定完成')
    await router.replace('/home')
  } catch (error) {
    fail(error, '身份绑定失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main class="onboarding-page">
    <header class="onboarding-header">
      <h1 class="onboarding-title">首次登录设置</h1>
      <p class="onboarding-sub">所属公司：{{ auth.onboarding?.company_name || '—' }}</p>
    </header>

    <ol class="steps">
      <li :class="['step', { active: step === 1 }]">1 修改初始密码</li>
      <li :class="['step', { active: step === 2 }]">2 身份绑定</li>
    </ol>

    <form v-if="step === 1" class="panel" @submit.prevent="onSubmitPassword">
      <h2 class="panel-title">修改初始密码</h2>
      <p class="panel-note">首次登录必须修改公司分配的临时密码。</p>
      <van-field
        v-model="passwordForm.password"
        label="新密码"
        type="password"
        placeholder="至少 8 位"
        autocomplete="new-password"
      />
      <van-field
        v-model="passwordForm.confirm"
        label="确认密码"
        type="password"
        placeholder="再次输入新密码"
        autocomplete="new-password"
      />
      <van-button class="submit" type="primary" native-type="submit" block :loading="saving">
        确认修改
      </van-button>
    </form>

    <form v-else class="panel" @submit.prevent="onSubmitBinding">
      <h2 class="panel-title">身份绑定</h2>
      <p class="panel-note">补全身份与驾驶资格资料后进入工作台，提交后由平台审核。</p>
      <van-field v-model="bindingForm.name" label="姓名" placeholder="请输入真实姓名" />
      <van-field v-model="bindingForm.id_number" label="身份证号" placeholder="请输入身份证号" />
      <van-field v-model="bindingForm.license_no" label="驾驶证号" placeholder="请输入驾驶证号" />
      <van-field v-model="bindingForm.license_type" label="准驾车型" placeholder="如 B2" />
      <van-field v-model="bindingForm.license_expiry" label="有效期" placeholder="ISO 8601 日期" />
      <van-button class="submit" type="primary" native-type="submit" block :loading="saving">
        完成绑定并进入
      </van-button>
    </form>
  </main>
</template>

<style scoped>
.onboarding-page {
  padding: var(--space-6) var(--space-4);
}

.onboarding-header {
  margin-bottom: var(--space-6);
}

.onboarding-title {
  margin: 0 0 var(--space-1);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.onboarding-sub {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.steps {
  display: flex;
  gap: var(--space-3);
  margin: 0 0 var(--space-4);
  padding: 0;
  list-style: none;
}

.step {
  flex: 1;
  padding: var(--space-2);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.step.active {
  color: var(--color-accent);
  border-color: var(--color-accent);
  font-weight: 600;
}

.panel {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.panel-title {
  margin: 0 0 var(--space-1);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.panel-note {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.submit {
  margin-top: var(--space-6);
  min-height: var(--tap-min);
}
</style>
