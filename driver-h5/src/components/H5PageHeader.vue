<script setup lang="ts">
import { useRouter } from 'vue-router'

interface Props {
  title: string
  showBack?: boolean
}

const { title, showBack = true } = defineProps<Props>()
const router = useRouter()
</script>

<template>
  <header class="h5-page-header">
    <button
      v-if="showBack"
      class="h5-page-header__back"
      type="button"
      aria-label="返回"
      @click="router.back()"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M15 5 8 12l7 7" />
      </svg>
    </button>
    <span class="h5-page-header__title">{{ title }}</span>
  </header>
</template>

<style scoped>
.h5-page-header {
  display: flex;
  align-items: center;
  height: 44px;
  padding: 0 var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  flex: 0 0 auto;
}
.h5-page-header__back {
  display: grid;
  place-items: center;
  width: var(--tap-min);
  height: var(--tap-min);
  margin-right: var(--space-2);
  margin-left: calc(-1 * var(--space-3));
  border: 0;
  background: transparent;
  color: var(--color-text-2);
  cursor: pointer;
}
.h5-page-header__back svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.h5-page-header__title { font-size: var(--font-size-md); font-weight: 600; }
</style>
