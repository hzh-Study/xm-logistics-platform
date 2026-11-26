<script setup lang="ts">
import { ref } from 'vue'

type UploadStatus = 'idle' | 'done'

interface Props {
  label: string
  multiple?: boolean
  status?: UploadStatus
}

const emit = defineEmits<{ (e: 'change', files: File[]): void }>()
const { label, multiple = false, status = 'idle' } = defineProps<Props>()
const inputRef = ref<HTMLInputElement | null>(null)

function onChange(event: Event): void {
  const target = event.target as HTMLInputElement
  emit('change', Array.from(target.files ?? []))
}
</script>

<template>
  <div>
    <span class="h5-uploader__label">{{ label }}</span>
    <button class="h5-uploader" :class="{ 'h5-uploader--done': status === 'done' }" type="button" @click="inputRef?.click()">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 16V4M8 8l4-4 4 4" />
        <path d="M4 16v4h16v-4" />
      </svg>
      <span>{{ status === 'done' ? '已选择文件' : '点击上传' }}</span>
    </button>
    <input ref="inputRef" class="h5-uploader__input" type="file" :multiple="multiple" @change="onChange" />
  </div>
</template>

<style scoped>
.h5-uploader__label {
  display: block;
  margin: var(--space-3) 0 var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-2);
  font-weight: 500;
}
.h5-uploader {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  width: 100%;
  min-height: 72px;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-3);
  font-size: var(--font-size-xs);
  cursor: pointer;
}
.h5-uploader--done {
  border-style: solid;
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-soft);
}
.h5-uploader svg {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.h5-uploader__input { display: none; }
</style>
