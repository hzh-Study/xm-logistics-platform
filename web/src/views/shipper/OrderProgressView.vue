<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getShipperProgress } from '@/api/checkin'
import { fetchOrder } from '@/api/order'
import PageHeader from '@/components/PageHeader.vue'
import NoticeBar from '@/components/NoticeBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import ProcessStepper from '@/components/ProcessStepper.vue'
import ProcessTimeline from '@/components/ProcessTimeline.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { ProcessStep } from '@/components/ProcessStepper.vue'
import type { TimelineItem } from '@/components/ProcessTimeline.vue'
import type { Order } from '@/types/order'
import type { TaskProgress } from '@/types/checkin'

const route = useRoute()
const orderId = Number(route.params.orderId)
const order = ref<Order | null>(null)
const progress = ref<TaskProgress | null>(null)
const loading = ref(false)

const steps = computed<ProcessStep[]>(() => {
  const p = progress.value
  const o = order.value
  if (!p || !o) return []
  const flags = [
    true,
    o.status !== '待承接',
    Boolean(p.task_no),
    p.checkins.length > 0,
    p.arrival_checkins.length > 0,
    Boolean(p.signoff_voucher),
    Boolean(p.signoff_confirmation) || o.status === '已完成',
  ]
  const labels = ['发布', '承接', '派单', '起运', '到达收货地', '签收', '完成']
  const times = [
    stamp(o.created_at), stamp(o.accepted_at), '', stamp(p.checkins[0]?.arrived_at),
    stamp(p.arrival_checkins[0]?.arrived_at), stamp(p.signoff_voucher?.received_at),
    stamp(p.signoff_confirmation?.created_at),
  ]
  const current = flags.findIndex((item) => !item)
  return labels.map((label, index) => ({
    label,
    done: flags[index],
    current: index === current,
    time: times[index] || undefined,
  }))
})

const timeline = computed<TimelineItem[]>(() => {
  const p = progress.value
  if (!p) return []
  const items: TimelineItem[] = []
  p.checkins.forEach((item) => items.push({
    title: '发货地打卡',
    meta: `${stamp(item.arrived_at)} · ${item.position_status}${item.distance_m !== null ? ` · 距离快照 ${item.distance_m} 米` : ''}`,
    desc: item.notes || undefined,
    photos: item.photos,
  }))
  p.loading_photos.forEach((item) => items.push({ title: `装货照片 · ${item.phase}`, meta: stamp(item.created_at), photos: item.paths }))
  p.loading_anomalies.forEach((item) => items.push({ title: `装货异常 · ${item.kind}`, meta: stamp(item.created_at), desc: item.detail, photos: item.photos }))
  if (p.confirmation) items.push({ title: '起运确认', meta: stamp(p.confirmation.created_at), desc: `货物核对：${p.confirmation.cargo_confirmed ? '已完成' : '未完成'} · 车辆核对：${p.confirmation.vehicle_confirmed ? '已完成' : '未完成'}` })
  p.arrival_checkins.forEach((item) => items.push({
    title: '到达收货地打卡',
    meta: `${stamp(item.arrived_at)} · ${item.position_status}${item.distance_m !== null ? ` · 距离快照 ${item.distance_m} 米` : ''}`,
    desc: item.notes || undefined,
    photos: item.photos,
  }))
  if (p.signoff_voucher) items.push({ title: '签收凭证', meta: stamp(p.signoff_voucher.received_at), desc: `${p.signoff_voucher.receiver_name} · ${p.signoff_voucher.receiving_condition}`, photos: [...p.signoff_voucher.signature_photos, ...p.signoff_voucher.vouchers] })
  return items
})

function stamp(value: string | null | undefined): string {
  return value ? value.replace('T', ' ').slice(0, 16) : ''
}

function place(snapshot: { name: string; contact: string; phone: string; province: string; city: string; district: string; detail_address: string }): string {
  return `${snapshot.name} · ${snapshot.province}${snapshot.city}${snapshot.district}${snapshot.detail_address} · ${snapshot.contact} ${snapshot.phone}`
}

async function load(): Promise<void> {
  loading.value = true
  try {
    ;[order.value, progress.value] = await Promise.all([fetchOrder(orderId), getShipperProgress(orderId)])
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取运输进度失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading">
    <PageHeader title="订单进度" :subtitle="`${order?.order_no ?? '—'} · 只读`" />

    <template v-if="order && progress">
      <section class="panel">
        <div class="panel-head"><span class="panel-title">订单基本信息</span></div>
        <div class="panel-body">
          <dl class="kv">
            <dt>订单编号</dt><dd class="num">{{ order.order_no }}</dd>
            <dt>订单状态</dt><dd><StatusPill :text="order.status" /></dd>
            <dt>货物</dt><dd>{{ [order.cargo_name, order.quantity, order.weight].filter(Boolean).join(' · ') }}</dd>
            <dt>发货快照</dt><dd>{{ place(order.shipping_snapshot) }}</dd>
            <dt>收货快照</dt><dd>{{ place(order.receiving_snapshot) }}</dd>
            <dt>运费报价</dt><dd class="num">{{ order.quote_method }} · {{ order.quote_amount_yuan }} 元</dd>
            <dt>发布时间</dt><dd class="num">{{ stamp(order.created_at) }}</dd>
          </dl>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head"><span class="panel-title">运输进度</span><span class="panel-hint">当前节点：{{ steps.find((step) => step.current)?.label ?? '已完成' }}</span></div>
        <div class="panel-body"><ProcessStepper :steps="steps" /></div>
      </section>

      <section class="panel">
        <div class="panel-head"><span class="panel-title">运输过程记录</span><span class="panel-hint">货主只读，不可修改司机提交的打卡与凭证</span></div>
        <div class="panel-body">
          <EmptyState v-if="!timeline.length" text="暂无运输过程记录" />
          <ProcessTimeline v-else :items="timeline" />
        </div>
      </section>

      <section v-if="progress.task_no" class="panel">
        <div class="panel-head"><span class="panel-title">关联运输任务</span></div>
        <div class="panel-body panel-body--tight">
          <div class="table-wrap">
            <table class="data-table">
              <thead><tr><th>任务编号</th><th>司机 / 车辆</th><th>任务状态</th><th class="num">计划装货</th><th class="num">计划送达</th></tr></thead>
              <tbody>
                <tr>
                  <td class="num">{{ progress.task_no }}</td>
                  <td>—</td>
                  <td><StatusPill :text="progress.task_status" /></td>
                  <td class="num">{{ stamp(progress.planned_load_at) }}</td>
                  <td class="num">{{ stamp(progress.planned_deliver_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </template>

    <NoticeBar v-else-if="!loading" tone="warning">暂无运输进度数据。</NoticeBar>
  </section>
</template>

<style scoped>
.kv { max-width: 760px; }
</style>
