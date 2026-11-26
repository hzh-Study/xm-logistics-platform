<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { changePassword, completeBinding } from '@/api/driver'
import { useAuthStore } from '@/stores/auth'
import H5PageHeader from '@/components/H5PageHeader.vue'
import H5Stepper from '@/components/H5Stepper.vue'
import H5Card from '@/components/H5Card.vue'
import H5BottomBar from '@/components/H5BottomBar.vue'
import H5Uploader from '@/components/H5Uploader.vue'
import type { DriverBindingPayload } from '@/types/driver'

const auth = useAuthStore()
const router = useRouter()
const saving = ref(false)
const step = ref<1 | 2 | 3>(auth.onboarding?.must_change_password ? 1 : 2)

const passwordForm = reactive({ current: '', password: '', confirm: '' })
const bindingForm = reactive<DriverBindingPayload>({
  name: '', id_number: '', license_no: '', license_type: '', license_expiry: '',
})
const idPhoto = ref('')

const licenseTypes = ['A1', 'A2', 'B2', 'C1']
const companyName = computed(() => auth.onboarding?.company_name ?? '')
const accountStatus = computed(() => auth.user?.account_status ?? '正常使用')
const employment = computed(() => '在职')

function fail(error: unknown, fallback: string): void {
  showToast(error instanceof Error ? error.message : fallback)
}

function onFileChange(files: File[]): void {
  idPhoto.value = files[0]?.name ?? ''
}

async function next(): Promise<void> {
  if (saving.value) return
  saving.value = true
  try {
    if (step.value === 1) {
      if (passwordForm.password.length < 8) {
        showToast('新密码不少于 8 位，需包含字母与数字')
        return
      }
      if (passwordForm.password !== passwordForm.confirm) {
        showToast('两次输入的新密码不一致')
        return
      }
      await changePassword(passwordForm.password)
      await auth.refreshOnboarding()
      showToast('密码已修改，请补全身份与驾驶证资料')
      step.value = 2
    } else if (step.value === 2) {
      if (!bindingForm.name.trim() || !bindingForm.id_number.trim() || !bindingForm.license_no.trim() || !bindingForm.license_type) {
        showToast('请完整填写真实姓名、身份证号、准驾车型与驾驶证号')
        return
      }
      step.value = 3
    } else {
      await completeBinding({ ...bindingForm })
      await auth.refreshOnboarding()
      showToast('身份绑定完成')
      await router.replace('/home')
    }
  } catch (error) {
    fail(error, step.value === 1 ? '修改密码失败' : '身份绑定失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="h5-page h5-page--with-bar">
    <H5PageHeader title="身份绑定" :show-back="false" />
    <main class="h5-scroll">
      <H5Stepper :current="step" />

      <H5Card v-if="step === 1">
        <h2 class="ob-title">修改初始密码</h2>
        <p class="ob-hint">首次登录必须修改临时密码</p>
        <label class="h5-label">当前临时密码</label>
        <van-field v-model="passwordForm.current" type="password" placeholder="请输入当前临时密码" />
        <label class="h5-label"><span class="h5-req">*</span>新密码</label>
        <van-field v-model="passwordForm.password" type="password" placeholder="请输入新密码" />
        <label class="h5-label"><span class="h5-req">*</span>确认新密码</label>
        <van-field v-model="passwordForm.confirm" type="password" placeholder="请再次输入新密码" />
        <p class="h5-help">新密码不少于 8 位，包含字母与数字。</p>
      </H5Card>

      <template v-else-if="step === 2">
        <H5Card>
          <h2 class="ob-title">身份与驾照资料</h2>
          <label class="h5-label"><span class="h5-req">*</span>真实姓名</label>
          <van-field v-model="bindingForm.name" placeholder="请输入真实姓名" />
          <label class="h5-label"><span class="h5-req">*</span>身份证号</label>
          <van-field v-model="bindingForm.id_number" placeholder="请输入身份证号" />
          <label class="h5-label"><span class="h5-req">*</span>准驾车型</label>
          <van-field name="license_type" label="准驾车型">
            <template #input>
              <van-radio-group v-model="bindingForm.license_type" direction="horizontal">
                <van-radio v-for="item in licenseTypes" :key="item" :name="item">{{ item }}</van-radio>
              </van-radio-group>
            </template>
          </van-field>
          <label class="h5-label"><span class="h5-req">*</span>驾驶证号</label>
          <van-field v-model="bindingForm.license_no" placeholder="请输入驾驶证号" />
          <label class="h5-label">驾驶证有效期</label>
          <van-field v-model="bindingForm.license_expiry" placeholder="YYYY-MM-DD" />
          <H5Uploader label="身份证 / 驾驶证照片" multiple @change="onFileChange" />
          <p v-if="idPhoto" class="h5-help">已选择：{{ idPhoto }}（凭证路径暂不随绑定提交）</p>
        </H5Card>
      </template>

      <H5Card v-else>
        <h2 class="ob-title">确认绑定信息</h2>
        <div class="h5-row"><span class="k">姓名</span><span class="v">{{ bindingForm.name }}</span></div>
        <div class="h5-row"><span class="k">所属公司</span><span class="v">{{ companyName }}</span></div>
        <div class="h5-row"><span class="k">准驾车型</span><span class="v">{{ bindingForm.license_type }}</span></div>
        <div class="h5-row"><span class="k">账号状态</span><span class="v">{{ accountStatus }}</span></div>
        <div class="h5-row"><span class="k">雇佣关系</span><span class="v">{{ employment }}</span></div>
        <p class="ob-hint">确认后完成身份绑定，公司归属不可自行变更。</p>
      </H5Card>
    </main>

    <H5BottomBar>
      <van-button v-if="step > 1" block @click="step = step === 3 ? 2 : 1">上一步</van-button>
      <van-button block type="primary" :loading="saving" @click="next">{{ step === 3 ? '完成绑定' : '下一步' }}</van-button>
    </H5BottomBar>
  </div>
</template>

<style scoped>
.ob-title { margin: 0 0 var(--space-2); font-size: var(--font-size-md); font-weight: 600; }
.ob-hint { margin: 0 0 var(--space-3); font-size: var(--font-size-sm); color: var(--color-text-3); }
</style>
