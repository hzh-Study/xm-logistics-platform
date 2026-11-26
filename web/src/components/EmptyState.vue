<script setup lang="ts">
interface Props {
  text: string
}

defineProps<Props>()
</script>

<template>
  <div class="empty-state" role="status">
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7h16v13H4z" />
      <path d="M3 7h18M9 7V4h6v3M9 12h6M9 16h4" />
    </svg>
    <span>{{ text }}</span>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-12) var(--space-5);
  color: var(--color-text-3);
  font-size: var(--font-size-sm);
}
.empty-state svg {
  width: 32px;
  height: 32px;
  fill: none;
  stroke: var(--color-border-strong);
  stroke-width: 1.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
