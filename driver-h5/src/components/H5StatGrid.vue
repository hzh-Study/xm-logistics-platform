<script setup lang="ts">
export interface H5StatItem {
  value: string | number
  label: string
}

interface Props {
  items: H5StatItem[]
}

defineProps<Props>()
</script>

<template>
  <div class="h5-stat-grid">
    <div v-for="(item, index) in items" :key="`${item.label}-${index}`" class="h5-stat-grid__item">
      <strong>{{ item.value }}</strong>
      <span>{{ item.label }}</span>
    </div>
  </div>
</template>

<style scoped>
.h5-stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-2); }
.h5-stat-grid__item {
  padding: var(--space-3) var(--space-2);
  text-align: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}
.h5-stat-grid__item strong {
  display: block;
  font-size: 20px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.h5-stat-grid__item span { font-size: var(--font-size-xs); color: var(--color-text-3); }
@media (max-width: 360px) {
  .h5-stat-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
