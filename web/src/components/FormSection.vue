<script setup lang="ts">
interface Props {
  title: string
}

defineProps<Props>()
</script>

<template>
  <section class="form-section">
    <h2 class="form-section__title">{{ title }}</h2>
    <div class="form-section__body"><slot /></div>
  </section>
</template>

<style scoped>
.form-section {
  margin-bottom: var(--space-4);
  padding: var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}
.form-section__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-4);
  font-size: var(--font-size-md);
  font-weight: 600;
}
.form-section__title::before {
  content: '';
  width: 3px;
  height: 16px;
  background: var(--color-accent);
  border-radius: 2px;
}
</style>
