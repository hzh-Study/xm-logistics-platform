<script setup lang="ts">
interface Props {
  text: string
}

defineProps<Props>()
</script>

<template>
  <div class="h5-empty-state" role="status">
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7h16v13H4z" />
      <path d="M3 7h18M9 7V4h6v3" />
    </svg>
    <span>{{ text }}</span>
  </div>
</template>

<style scoped>
.h5-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-10) var(--space-4);
  color: var(--color-text-3);
  font-size: var(--font-size-sm);
}
.h5-empty-state svg {
  width: 32px;
  height: 32px;
  fill: none;
  stroke: var(--color-border-strong);
  stroke-width: 1.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
