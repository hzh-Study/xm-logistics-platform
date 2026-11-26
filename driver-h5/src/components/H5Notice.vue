<script setup lang="ts">
type Tone = 'info' | 'warning' | 'error'

interface Props {
  tone?: Tone
}

const { tone = 'info' } = defineProps<Props>()
</script>

<template>
  <div class="h5-notice" :class="`h5-notice--${tone}`" role="status">
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5l-8-3Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
    <span><slot /></span>
  </div>
</template>

<style scoped>
.h5-notice {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-control);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}
.h5-notice svg {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  margin-top: 1px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.h5-notice--info { background: var(--color-accent-soft); color: var(--color-accent-hover); }
.h5-notice--warning { background: var(--color-warning-soft); color: var(--color-warning); }
.h5-notice--error { background: var(--color-error-soft); color: var(--color-error); }
</style>
