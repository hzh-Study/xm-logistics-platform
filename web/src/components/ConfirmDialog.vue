<script setup lang="ts">
import { nextTick, watch } from 'vue'

interface Props {
  modelValue: boolean
  title: string
  message?: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
}

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
}>()

const { modelValue, confirmText = '确认', cancelText = '取消', danger = false } = defineProps<Props>()

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

function onConfirm(): void {
  emit('confirm')
  close()
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="min(460px, 92vw)"
    align-center
    class="confirm-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="message || $slots.default" class="confirm-dialog__message">
      <slot>{{ message }}</slot>
    </div>
    <template #footer>
      <el-button @click="close">{{ cancelText }}</el-button>
      <el-button :type="danger ? 'danger' : 'primary'" @click="onConfirm">{{ confirmText }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.confirm-dialog__message {
  font-size: var(--font-size-md);
  color: var(--color-text-2);
  line-height: 1.6;
}
</style>
