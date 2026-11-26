<script setup lang="ts">
import PhotoGrid from '@/components/PhotoGrid.vue'

export interface TimelineItem {
  title: string
  meta: string
  desc?: string
  photos?: string[]
  labels?: string[]
}

interface Props {
  items: TimelineItem[]
}

defineProps<Props>()
</script>

<template>
  <div class="process-timeline">
    <div v-for="(item, index) in items" :key="`${item.title}-${index}`" class="process-timeline__item">
      <div class="process-timeline__title">{{ item.title }}</div>
      <div class="process-timeline__meta">{{ item.meta }}</div>
      <div v-if="item.desc" class="process-timeline__desc">{{ item.desc }}</div>
      <PhotoGrid v-if="item.photos?.length" :photos="item.photos" :labels="item.labels" />
    </div>
  </div>
</template>

<style scoped>
.process-timeline { position: relative; padding-left: var(--space-5); }
.process-timeline::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 6px;
  bottom: 6px;
  width: 1px;
  background: var(--color-border);
}
.process-timeline__item { position: relative; padding-bottom: var(--space-5); }
.process-timeline__item:last-child { padding-bottom: 0; }
.process-timeline__item::before {
  content: '';
  position: absolute;
  left: -21px;
  top: 5px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--color-accent);
  border: 2px solid var(--color-accent);
  z-index: 1;
}
.process-timeline__title { font-size: var(--font-size-md); font-weight: 500; }
.process-timeline__meta {
  margin-top: 2px;
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
  font-variant-numeric: tabular-nums;
}
.process-timeline__desc {
  margin-top: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-2);
}
</style>
