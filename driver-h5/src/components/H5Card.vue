<script setup lang="ts"></script>

<template>
  <section class="h5-card">
    <slot />
  </section>
</template>

<style scoped>
.h5-card {
  margin-bottom: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}
.h5-card:last-child { margin-bottom: 0; }
</style>
