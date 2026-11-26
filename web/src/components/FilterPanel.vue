<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  collapsed?: boolean
}

const { collapsed = false } = defineProps<Props>()
const open = ref(!collapsed)
</script>

<template>
  <section class="filter-panel" :class="{ 'filter-panel--collapsed': !open }">
    <header class="filter-panel__head">
      <span class="filter-panel__title">筛选条件</span>
      <button class="filter-panel__toggle" type="button" @click="open = !open">
        {{ open ? '收起筛选' : '展开筛选' }}
      </button>
    </header>
    <div v-if="open" class="filter-panel__body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.filter-panel {
  margin-bottom: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}
.filter-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 44px;
  padding: 0 var(--space-4);
}
.filter-panel__title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-2);
}
.filter-panel__toggle {
  border: 0;
  background: transparent;
  color: var(--color-accent);
  font-size: var(--font-size-sm);
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-control);
}
.filter-panel__toggle:hover { background: var(--color-accent-soft); }
.filter-panel__body { padding: 0 var(--space-4) var(--space-4); }
</style>
