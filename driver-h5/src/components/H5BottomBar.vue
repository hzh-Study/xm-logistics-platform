<script setup lang="ts"></script>

<template>
  <footer class="h5-bottom-bar">
    <slot />
  </footer>
</template>

<style scoped>
.h5-bottom-bar {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4) calc(var(--space-3) + var(--safe-bottom));
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  flex: 0 0 auto;
}
/* NOTE: 让底部通栏按钮在 H5 默认达到 44px 触控高度。 */
:deep(.van-button) { flex: 1; height: var(--tap-min); font-size: 15px; }
</style>
