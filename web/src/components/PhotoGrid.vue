<script setup lang="ts">
interface Props {
  photos: string[]
  labels?: string[]
}

const { photos, labels } = defineProps<Props>()
</script>

<template>
  <div v-if="photos.length" class="photo-grid">
    <div v-for="(photo, index) in photos" :key="`${photo}-${index}`" class="photo-grid__item">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <circle cx="8.5" cy="9.5" r="1.5" />
        <path d="m4 17 5-5 4 4 3-3 4 4" />
      </svg>
      <span class="photo-grid__label">{{ labels?.[index] ?? `凭证 ${index + 1}` }}</span>
    </div>
  </div>
</template>

<style scoped>
.photo-grid { display: flex; gap: var(--space-2); flex-wrap: wrap; margin-top: var(--space-2); }
.photo-grid__item {
  width: 72px;
  height: 72px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-fill);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--color-text-3);
  font-size: 11px;
}
.photo-grid__item svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.photo-grid__label { max-width: 64px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
