<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormItemRule } from 'element-plus'
import * as orderApi from '@/api/order'
import * as warehouseApi from '@/api/warehouse'
import PageHeader from '@/components/PageHeader.vue'
import FormSection from '@/components/FormSection.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import type { PublishInput, QuoteMethod } from '@/types/order'
import type { Warehouse } from '@/types/warehouse'

const router = useRouter()
const formRef = ref<FormInstance | null>(null)
const saving = ref(false)
const warehouses = ref<Warehouse[]>([])
const confirmOpen = ref(false)

const form = reactive({
  cargo_name: '',
  cargo_type: '',
  quantity: '',
  weight: '',
  volume: '',
  packaging: '',
  photo_text: '',
  cargo_remarks: '',
  shipping_source: '临时地址' as '仓库' | '临时地址',
  warehouse_id: undefined as number | undefined,
  shipping_name: '',
  shipping_contact: '',
  shipping_phone: '',
  shipping_province: '',
  shipping_city: '',
  shipping_district: '',
  shipping_detail_address: '',
  receiving_name: '',
  receiving_contact: '',
  receiving_phone: '',
  receiving_province: '',
  receiving_city: '',
  receiving_district: '',
  receiving_detail_address: '',
  vehicle_type: '',
  vehicle_length: '',
  load_requirement: '',
  cold_chain: false,
  rain_protection: false,
  enclosed_body: false,
  special_loading: false,
  other_services: '',
  transport_remarks: '',
  quote_method: '可协商' as QuoteMethod,
  quote_amount_yuan: '',
  accept_bargain: false,
  quote_remarks: '',
})

const CARGO_TYPES = ['钢材', '建材', '机电设备', '化工品', '冷链食品', '其他']
const PACKAGINGS = ['裸装', '木箱', '托盘', '编织袋', '其他']
const VEHICLE_TYPES = ['平板车', '厢式货车', '高栏车', '自卸车']
const VEHICLE_LENGTHS = ['4.2 米', '6.8 米', '9.6 米', '13 米']
const QUOTE_LABELS: Record<QuoteMethod, string> = { 固定: '固定价', 可协商: '可议', 其他: '其它' }

const required = (message: string): FormItemRule[] => [{ required: true, message, trigger: 'blur' }]

const rules = computed<Record<string, FormItemRule[]>>(() => ({
  cargo_name: required('请填写货物名称'),
  receiving_name: required('请填写收货方名称'),
  receiving_contact: required('请填写收货联系人'),
  receiving_phone: required('请填写收货联系电话'),
  receiving_province: required('请填写收货省份'),
  receiving_city: required('请填写收货城市'),
  receiving_district: required('请填写收货区县'),
  receiving_detail_address: required('请填写收货详细地址'),
  ...(form.shipping_source === '仓库'
    ? { warehouse_id: [{ required: true, message: '请选择发货仓库', trigger: 'change' }] }
    : {
        shipping_name: required('请填写发货点名称'),
        shipping_contact: required('请填写发货联系人'),
        shipping_phone: required('请填写发货联系电话'),
        shipping_province: required('请填写发货省份'),
        shipping_city: required('请填写发货城市'),
        shipping_district: required('请填写发货区县'),
        shipping_detail_address: required('请填写发货详细地址'),
      }),
  ...(form.quote_method === '固定' ? { quote_amount_yuan: required('固定报价请填写金额（元）') } : {}),
}))

const shippingSummary = computed(() => {
  if (form.shipping_source === '仓库') {
    const warehouse = warehouses.value.find((item) => item.id === form.warehouse_id)
    return warehouse ? `${warehouse.name} · ${warehouse.location}` : '—'
  }
  return [form.shipping_name, form.shipping_province, form.shipping_city, form.shipping_detail_address].filter(Boolean).join(' · ')
})

const receivingSummary = computed(() =>
  [form.receiving_province, form.receiving_city, form.receiving_district, form.receiving_detail_address, form.receiving_contact, form.receiving_phone]
    .filter(Boolean).join(' · '),
)

const requirementSummary = computed(() => {
  const flags = [form.cold_chain && '冷链', form.rain_protection && '防雨', form.enclosed_body && '封闭式车厢', form.special_loading && '特殊装卸'].filter(Boolean)
  return [form.vehicle_type, form.vehicle_length, form.load_requirement && `载重 ${form.load_requirement} 吨`, ...flags].filter(Boolean).join(' / ')
})

const quoteSummary = computed(() =>
  form.quote_method === '固定'
    ? `¥ ${form.quote_amount_yuan || '0.00'}（${QUOTE_LABELS[form.quote_method]}）`
    : QUOTE_LABELS[form.quote_method],
)

onMounted(async () => {
  try {
    warehouses.value = await warehouseApi.fetchWarehouses(undefined, '正常')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载仓库失败')
  }
})

function buildPayload(): PublishInput {
  const payload: PublishInput = {
    cargo_name: form.cargo_name.trim(),
    cargo_type: form.cargo_type.trim(),
    quantity: form.quantity.trim(),
    weight: form.weight.trim(),
    volume: form.volume.trim(),
    packaging: form.packaging.trim(),
    cargo_photos: form.photo_text.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
    cargo_remarks: form.cargo_remarks.trim(),
    shipping_source: form.shipping_source,
    receiving_name: form.receiving_name.trim(),
    receiving_contact: form.receiving_contact.trim(),
    receiving_phone: form.receiving_phone.trim(),
    receiving_province: form.receiving_province.trim(),
    receiving_city: form.receiving_city.trim(),
    receiving_district: form.receiving_district.trim(),
    receiving_detail_address: form.receiving_detail_address.trim(),
    vehicle_type: form.vehicle_type.trim(),
    vehicle_length: form.vehicle_length.trim(),
    load_requirement: form.load_requirement.trim(),
    cold_chain: form.cold_chain,
    rain_protection: form.rain_protection,
    enclosed_body: form.enclosed_body,
    special_loading: form.special_loading,
    other_services: form.other_services.trim(),
    transport_remarks: form.transport_remarks.trim(),
    quote_method: form.quote_method,
    accept_bargain: form.accept_bargain,
    quote_remarks: form.quote_remarks.trim(),
  }
  if (form.shipping_source === '仓库') {
    payload.warehouse_id = form.warehouse_id
  } else {
    payload.shipping_name = form.shipping_name.trim()
    payload.shipping_contact = form.shipping_contact.trim()
    payload.shipping_phone = form.shipping_phone.trim()
    payload.shipping_province = form.shipping_province.trim()
    payload.shipping_city = form.shipping_city.trim()
    payload.shipping_district = form.shipping_district.trim()
    payload.shipping_detail_address = form.shipping_detail_address.trim()
  }
  if (form.quote_method === '固定') payload.quote_amount_yuan = form.quote_amount_yuan.trim()
  return payload
}

async function openConfirm(): Promise<void> {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  confirmOpen.value = true
}

async function publish(): Promise<void> {
  saving.value = true
  try {
    const order = await orderApi.publishOrder(buildPayload())
    ElMessage.success(`发布成功，订单号 ${order.order_no}，已进入待承接`)
    await router.push('/shipper/orders')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '发布失败，请稍后重试')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section>
    <PageHeader title="发布运输订单" subtitle="发布前需确认全部信息；发货与收货信息将固化为快照" />

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <FormSection title="货物信息">
        <div class="form-grid">
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>货物名称</label>
            <el-input v-model="form.cargo_name" placeholder="如：热轧钢板" />
          </div>
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>货物类型</label>
            <el-select v-model="form.cargo_type" placeholder="全部" clearable>
              <el-option v-for="item in CARGO_TYPES" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>数量</label><el-input v-model="form.quantity" placeholder="如：32 吨" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>重量（吨）</label><el-input v-model="form.weight" placeholder="如：32" /></div>
          <div class="field"><label class="field__label">体积（m³）</label><el-input v-model="form.volume" /></div>
          <div class="field">
            <label class="field__label">包装</label>
            <el-select v-model="form.packaging" placeholder="全部" clearable>
              <el-option v-for="item in PACKAGINGS" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field field--wide">
            <label class="field__label">货物照片</label>
            <el-input v-model="form.photo_text" placeholder="库内相对路径，多个用逗号分隔" />
            <p class="field__help">凭证仅存库内相对路径，不上传绝对路径。</p>
          </div>
          <div class="field field--wide"><label class="field__label">备注</label><el-input v-model="form.cargo_remarks" type="textarea" :rows="2" /></div>
        </div>
      </FormSection>

      <FormSection title="发货信息（发货快照）">
        <div class="field">
          <span class="field__label"><span class="field__req">*</span>发货方式</span>
          <el-radio-group v-model="form.shipping_source">
            <el-radio value="仓库">选择已有仓库</el-radio>
            <el-radio value="临时地址">临时地址</el-radio>
          </el-radio-group>
        </div>
        <div v-if="form.shipping_source === '仓库'" class="field">
          <label class="field__label"><span class="field__req">*</span>发货仓库</label>
          <el-select v-model="form.warehouse_id" placeholder="全部" style="width: 320px">
            <el-option v-for="w in warehouses" :key="w.id" :label="`${w.name} · ${w.location}`" :value="w.id" />
          </el-select>
        </div>
        <div v-else class="form-grid">
          <div class="field"><label class="field__label"><span class="field__req">*</span>发货点名称</label><el-input v-model="form.shipping_name" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>联系人</label><el-input v-model="form.shipping_contact" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>联系电话</label><el-input v-model="form.shipping_phone" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>省份</label><el-input v-model="form.shipping_province" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>城市</label><el-input v-model="form.shipping_city" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>区县</label><el-input v-model="form.shipping_district" /></div>
          <div class="field field--wide"><label class="field__label"><span class="field__req">*</span>详细地址</label><el-input v-model="form.shipping_detail_address" /></div>
        </div>
        <div class="readonly-box">发布时固化以下信息为<b>发货快照</b>，后续仓库改名、停用或删除均不回写：{{ shippingSummary }}</div>
      </FormSection>

      <FormSection title="收货信息（收货快照）">
        <div class="form-grid">
          <div class="field"><label class="field__label"><span class="field__req">*</span>收货联系人</label><el-input v-model="form.receiving_contact" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>收货电话</label><el-input v-model="form.receiving_phone" /></div>
          <div class="field field--wide"><label class="field__label"><span class="field__req">*</span>收货地址</label><el-input v-model="form.receiving_name" placeholder="收货方名称" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>省份</label><el-input v-model="form.receiving_province" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>城市</label><el-input v-model="form.receiving_city" /></div>
          <div class="field"><label class="field__label"><span class="field__req">*</span>区县</label><el-input v-model="form.receiving_district" /></div>
          <div class="field field--wide"><label class="field__label"><span class="field__req">*</span>详细地址</label><el-input v-model="form.receiving_detail_address" /></div>
        </div>
        <div class="readonly-box">发布时固化为<b>收货快照</b>：{{ receivingSummary }}</div>
      </FormSection>

      <FormSection title="运输要求">
        <div class="form-grid">
          <div class="field">
            <label class="field__label">车型</label>
            <el-select v-model="form.vehicle_type" placeholder="全部" clearable>
              <el-option v-for="item in VEHICLE_TYPES" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field">
            <label class="field__label">车长</label>
            <el-select v-model="form.vehicle_length" placeholder="全部" clearable>
              <el-option v-for="item in VEHICLE_LENGTHS" :key="item" :label="item" :value="item" />
            </el-select>
          </div>
          <div class="field"><label class="field__label">载重要求（吨）</label><el-input v-model="form.load_requirement" /></div>
          <div class="field field--wide"><label class="field__label">特殊要求</label>
            <div class="check-row">
              <el-checkbox v-model="form.cold_chain">冷链</el-checkbox>
              <el-checkbox v-model="form.rain_protection">防雨</el-checkbox>
              <el-checkbox v-model="form.enclosed_body">封闭式车厢</el-checkbox>
              <el-checkbox v-model="form.special_loading">特殊装卸</el-checkbox>
            </div>
          </div>
          <div class="field"><label class="field__label">其它服务</label><el-input v-model="form.other_services" /></div>
          <div class="field"><label class="field__label">运输备注</label><el-input v-model="form.transport_remarks" /></div>
        </div>
      </FormSection>

      <FormSection title="运费报价">
        <NoticeBar tone="info">运费报价仅货主与物流公司可见，司机端不会展示该字段，也不构成双方结算。</NoticeBar>
        <div class="form-grid section-gap">
          <div class="field">
            <label class="field__label"><span class="field__req">*</span>报价方式</label>
            <el-select v-model="form.quote_method" style="width: 180px">
              <el-option label="固定价" value="固定" />
              <el-option label="可议" value="可协商" />
              <el-option label="其它" value="其他" />
            </el-select>
          </div>
          <div v-if="form.quote_method === '固定'" class="field">
            <label class="field__label"><span class="field__req">*</span>报价金额（元）</label>
            <el-input v-model="form.quote_amount_yuan" placeholder="如：12800.00" />
          </div>
          <div class="field field--wide">
            <div class="check-row">
              <el-checkbox v-model="form.accept_bargain">接受议价标记（在货源列表展示）</el-checkbox>
            </div>
          </div>
          <div class="field field--wide"><label class="field__label">报价备注</label><el-input v-model="form.quote_remarks" /></div>
        </div>
      </FormSection>

      <div class="form-actions page-actions">
        <el-button @click="router.push('/shipper/orders')">取消</el-button>
        <el-button type="primary" @click="openConfirm">发布前确认</el-button>
      </div>
    </el-form>

    <ConfirmDialog v-model="confirmOpen" title="确认发布运输订单" confirm-text="确认发布" :danger="false" @confirm="publish">
      <dl class="summary-list">
        <dt>货物</dt><dd>{{ form.cargo_name }} · {{ form.weight || form.quantity }} 吨 · {{ form.cargo_type }}</dd>
        <dt>发货快照</dt><dd>{{ shippingSummary }}</dd>
        <dt>收货快照</dt><dd>{{ receivingSummary }}</dd>
        <dt>运输要求</dt><dd>{{ requirementSummary }}</dd>
        <dt>运费报价</dt><dd>{{ quoteSummary }}</dd>
      </dl>
      <p class="confirm-note">发布后进入「待承接」，货源对所有已认证物流公司可见。</p>
    </ConfirmDialog>
  </section>
</template>

<style scoped>
.field--wide { grid-column: 1 / -1; }
.section-gap { margin-top: var(--space-4); }
.page-actions { margin-bottom: var(--space-6); }
.confirm-note { margin: var(--space-4) 0 0; color: var(--color-text-2); }
</style>
