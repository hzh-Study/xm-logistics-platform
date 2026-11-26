<script setup lang="ts">
import { nextTick, watch } from 'vue'

interface Props {
  modelValue: boolean
  title: string
}

const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()
const { modelValue } = defineProps<Props>()

let trigger: HTMLElement | null = null

watch(() => modelValue, (open) => {
  if (open) {
    trigger = document.activeElement as HTMLElement | null
  } else {
    void nextTick(() => trigger?.focus())
  }
})

function close(): void {
  emit('update:modelValue', false)
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    size="min(520px, 92vw)"
    :with-header="false"
    class="detail-drawer"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="detail-drawer__inner">
      <header class="detail-drawer__head">
        <span class="detail-drawer__title">{{ title }}</span>
        <button class="detail-drawer__close" type="button" aria-label="关闭抽屉" @click="close">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12M18 6 6 18" />
          </svg>
        </button>
      </header>
      <div class="detail-drawer__body"><slot name="body" /></div>
      <footer v-if="$slots.footer" class="detail-drawer__foot"><slot name="footer" /></footer>
    </div>
  </el-drawer>
</template>

<style scoped>
.detail-drawer__inner { display: flex; flex-direction: column; height: 100%; }
.detail-drawer__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 var(--space-5);
  border-bottom: 1px solid var(--color-border);
  flex: 0 0 auto;
}
.detail-drawer__title { font-size: var(--font-size-md); font-weight: 600; }
.detail-drawer__close {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-3);
  cursor: pointer;
}
.detail-drawer__close:hover { background: var(--color-fill); color: var(--color-text); }
.detail-drawer__close svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
}
.detail-drawer__body { flex: 1; overflow-y: auto; padding: var(--space-5); }
.detail-drawer__foot {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--color-border);
  flex: 0 0 auto;
}
/* NOTE: 穿透 el-drawer 内部默认内边距，使自定义头部与内容按设计系统铺满。 */
:deep(.el-drawer__body) { padding: 0; }
</style>
