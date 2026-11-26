<script setup lang="ts">
export interface ProcessStep {
  label: string
  done: boolean
  current: boolean
  time?: string
}

interface Props {
  steps: ProcessStep[]
}

defineProps<Props>()
</script>

<template>
  <div class="process-stepper">
    <div
      v-for="(step, index) in steps"
      :key="`${step.label}-${index}`"
      class="process-stepper__step"
      :class="{ 'is-done': step.done, 'is-current': step.current }"
    >
      <div class="process-stepper__dot">{{ step.done ? '✓' : index + 1 }}</div>
      <div class="process-stepper__label">{{ step.label }}</div>
      <div v-if="step.time" class="process-stepper__time">{{ step.time }}</div>
    </div>
  </div>
</template>

<style scoped>
.process-stepper { display: flex; align-items: flex-start; padding: var(--space-2) var(--space-1) 0; }
.process-stepper__step { flex: 1; position: relative; text-align: center; min-width: 0; }
.process-stepper__step::before {
  content: '';
  position: absolute;
  top: 13px;
  left: -50%;
  width: 100%;
  height: 2px;
  background: var(--color-border);
  z-index: 0;
}
.process-stepper__step:first-child::before { display: none; }
.process-stepper__step.is-done::before,
.process-stepper__step.is-current::before { background: var(--color-accent); }
.process-stepper__dot {
  position: relative;
  z-index: 1;
  width: 26px;
  height: 26px;
  margin: 0 auto var(--space-2);
  border-radius: 50%;
  background: var(--color-surface);
  border: 2px solid var(--color-border-strong);
  color: var(--color-text-3);
  display: grid;
  place-items: center;
  font-size: var(--font-size-xs);
  font-weight: 600;
}
.process-stepper__step.is-done .process-stepper__dot {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-surface);
}
.process-stepper__step.is-current .process-stepper__dot {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.process-stepper__label {
  font-size: var(--font-size-sm);
  color: var(--color-text-3);
  padding: 0 var(--space-1);
}
.process-stepper__step.is-done .process-stepper__label,
.process-stepper__step.is-current .process-stepper__label {
  color: var(--color-text);
  font-weight: 500;
}
.process-stepper__time {
  margin-top: 3px;
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
  font-variant-numeric: tabular-nums;
}
</style>
