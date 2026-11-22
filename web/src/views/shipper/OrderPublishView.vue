<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormItemRule } from 'element-plus'
import * as orderApi from '@/api/order'
import * as warehouseApi from '@/api/warehouse'
import type { PublishInput } from '@/types/order'
import type { Warehouse } from '@/types/warehouse'

const router = useRouter()
const formRef = ref<FormInstance | null>(null)
const saving = ref(false)
const warehouses = ref<Warehouse[]>([])

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
  quote_method: '可协商' as '固定' | '可协商' | '其他',
  quote_amount_yuan: '',
  accept_bargain: false,
  quote_remarks: '',
})

const required = (message: string): FormItemRule[] => [
  { required: true, message, trigger: 'blur' },
]

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
  ...(form.quote_method === '固定'
    ? { quote_amount_yuan: required('固定报价请填写金额（元）') }
    : {}),
}))

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
    cargo_photos: form.photo_text
      .split(/[,，]/)
      .map((item) => item.trim())
      .filter(Boolean),
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
  if (form.quote_method === '固定') {
    payload.quote_amount_yuan = form.quote_amount_yuan.trim()
  }
  return payload
}

async function onSubmit(): Promise<void> {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  try {
    await ElMessageBox.confirm('确认发布该运输订单？发布后发货与收货信息将固化为快照。', '发布确认', {
      type: 'warning',
    })
  } catch {
    return
  }
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
  <section class="publish">
    <h1 class="page-title">发布运输订单</h1>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <div class="group">
        <h2 class="group-title">货物信息</h2>
        <div class="grid">
          <el-form-item label="货物名称" prop="cargo_name">
            <el-input v-model="form.cargo_name" placeholder="如：冷轧钢板" />
          </el-form-item>
          <el-form-item label="货物类型">
            <el-input v-model="form.cargo_type" placeholder="如：钢材" />
          </el-form-item>
          <el-form-item label="数量">
            <el-input v-model="form.quantity" placeholder="如：50 吨" />
          </el-form-item>
          <el-form-item label="重量">
            <el-input v-model="form.weight" placeholder="如：50000 kg" />
          </el-form-item>
          <el-form-item label="体积">
            <el-input v-model="form.volume" placeholder="如：12.5 m³" />
          </el-form-item>
          <el-form-item label="包装">
            <el-input v-model="form.packaging" placeholder="如：钢带捆扎" />
          </el-form-item>
          <el-form-item label="照片路径">
            <el-input v-model="form.photo_text" placeholder="库内相对路径，逗号分隔" />
          </el-form-item>
          <el-form-item label="货物备注">
            <el-input v-model="form.cargo_remarks" placeholder="如：需防潮" />
          </el-form-item>
        </div>
      </div>

      <div class="group">
        <h2 class="group-title">发货信息</h2>
        <el-form-item label="发货方式">
          <el-radio-group v-model="form.shipping_source">
            <el-radio value="临时地址">临时地址</el-radio>
            <el-radio value="仓库">选择仓库</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.shipping_source === '仓库'" label="发货仓库" prop="warehouse_id">
          <el-select v-model="form.warehouse_id" placeholder="请选择可用仓库" style="width: 320px">
            <el-option v-for="w in warehouses" :key="w.id" :label="`${w.name} · ${w.location}`" :value="w.id" />
          </el-select>
        </el-form-item>
        <div v-else class="grid">
          <el-form-item label="发货点名称" prop="shipping_name">
            <el-input v-model="form.shipping_name" />
          </el-form-item>
          <el-form-item label="联系人" prop="shipping_contact">
            <el-input v-model="form.shipping_contact" />
          </el-form-item>
          <el-form-item label="联系电话" prop="shipping_phone">
            <el-input v-model="form.shipping_phone" />
          </el-form-item>
          <el-form-item label="省份" prop="shipping_province">
            <el-input v-model="form.shipping_province" />
          </el-form-item>
          <el-form-item label="城市" prop="shipping_city">
            <el-input v-model="form.shipping_city" />
          </el-form-item>
          <el-form-item label="区县" prop="shipping_district">
            <el-input v-model="form.shipping_district" />
          </el-form-item>
          <el-form-item label="详细地址" prop="shipping_detail_address">
            <el-input v-model="form.shipping_detail_address" />
          </el-form-item>
        </div>
      </div>

      <div class="group">
        <h2 class="group-title">收货信息</h2>
        <div class="grid">
          <el-form-item label="收货方名称" prop="receiving_name">
            <el-input v-model="form.receiving_name" />
          </el-form-item>
          <el-form-item label="联系人" prop="receiving_contact">
            <el-input v-model="form.receiving_contact" />
          </el-form-item>
          <el-form-item label="联系电话" prop="receiving_phone">
            <el-input v-model="form.receiving_phone" />
          </el-form-item>
          <el-form-item label="省份" prop="receiving_province">
            <el-input v-model="form.receiving_province" />
          </el-form-item>
          <el-form-item label="城市" prop="receiving_city">
            <el-input v-model="form.receiving_city" />
          </el-form-item>
          <el-form-item label="区县" prop="receiving_district">
            <el-input v-model="form.receiving_district" />
          </el-form-item>
          <el-form-item label="详细地址" prop="receiving_detail_address">
            <el-input v-model="form.receiving_detail_address" />
          </el-form-item>
        </div>
      </div>

      <div class="group">
        <h2 class="group-title">运输要求</h2>
        <div class="grid">
          <el-form-item label="车型">
            <el-input v-model="form.vehicle_type" placeholder="如：平板车" />
          </el-form-item>
          <el-form-item label="车长">
            <el-input v-model="form.vehicle_length" placeholder="如：13 米" />
          </el-form-item>
          <el-form-item label="载重">
            <el-input v-model="form.load_requirement" placeholder="如：30 吨以上" />
          </el-form-item>
          <el-form-item label="其他服务">
            <el-input v-model="form.other_services" placeholder="如：需叉车卸货" />
          </el-form-item>
          <el-form-item label="要求备注">
            <el-input v-model="form.transport_remarks" />
          </el-form-item>
        </div>
        <el-form-item label="特殊要求">
          <el-checkbox v-model="form.cold_chain">冷链</el-checkbox>
          <el-checkbox v-model="form.rain_protection">防雨</el-checkbox>
          <el-checkbox v-model="form.enclosed_body">厢式车身</el-checkbox>
          <el-checkbox v-model="form.special_loading">特殊装载</el-checkbox>
        </el-form-item>
      </div>

      <div class="group">
        <h2 class="group-title">运费报价</h2>
        <div class="grid">
          <el-form-item label="报价方式">
            <el-select v-model="form.quote_method" style="width: 180px">
              <el-option label="可协商" value="可协商" />
              <el-option label="固定" value="固定" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.quote_method === '固定'" label="金额（元）" prop="quote_amount_yuan">
            <el-input v-model="form.quote_amount_yuan" placeholder="如：1200.50" />
          </el-form-item>
          <el-form-item label="报价备注">
            <el-input v-model="form.quote_remarks" />
          </el-form-item>
        </div>
        <el-form-item label="展示标记">
          <el-checkbox v-model="form.accept_bargain">接受议价（仅展示，V1 无议价流程）</el-checkbox>
        </el-form-item>
      </div>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="onSubmit">确认发布</el-button>
        <el-button @click="router.push('/shipper/orders')">取消</el-button>
      </el-form-item>
    </el-form>
  </section>
</template>

<style scoped>
.publish {
  padding: var(--space-2) 0;
}

.page-title {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.group {
  margin-bottom: var(--space-4);
  padding: var(--space-4) var(--space-6) 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.group-title {
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-md);
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: var(--space-6);
}
</style>
