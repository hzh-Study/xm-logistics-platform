<script setup lang="ts">
interface Props {
  value: string | number
  label: string
}

defineProps<Props>()
</script>

<template>
  <div class="stat-card">
    <div class="stat-card__value">{{ value }}</div>
    <div class="stat-card__label">{{ label }}</div>
  </div>
</template>

<style scoped>
.stat-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  padding: var(--space-4) var(--space-5);
}
.stat-card__value {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.6px;
  font-variant-numeric: tabular-nums;
}
.stat-card__label {
  margin-top: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--color-text-3);
}
</style>
