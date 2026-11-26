<script setup lang="ts">
type Tone = 'info' | 'warning' | 'error'

interface Props {
  tone?: Tone
}

const { tone = 'info' } = defineProps<Props>()
</script>

<template>
  <div class="notice-bar" :class="`notice-bar--${tone}`" role="status">
    <svg class="notice-bar__icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5l-8-3Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
    <div class="notice-bar__content"><slot /></div>
  </div>
</template>

<style scoped>
.notice-bar {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-control);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}
.notice-bar__icon {
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
.notice-bar__content { min-width: 0; }
.notice-bar--info { background: var(--color-accent-soft); color: var(--color-accent-hover); }
.notice-bar--warning { background: var(--color-warning-soft); color: var(--color-warning); }
.notice-bar--error { background: var(--color-error-soft); color: var(--color-error); }
</style>
