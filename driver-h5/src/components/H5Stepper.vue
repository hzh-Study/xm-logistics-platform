<script setup lang="ts">
interface Props {
  current: 1 | 2 | 3
}

defineProps<Props>()

const steps = ['修改密码', '身份资料', '确认'] as const
</script>

<template>
  <div class="h5-stepper">
    <div
      v-for="(step, index) in steps"
      :key="step"
      class="h5-stepper__step"
      :class="{ 'is-on': current === index + 1, 'is-done': current > index + 1 }"
    >
      <i>{{ current > index + 1 ? '✓' : index + 1 }}</i>
      <span>{{ step }}</span>
    </div>
  </div>
</template>

<style scoped>
.h5-stepper { display: flex; align-items: center; padding: var(--space-1) 0 var(--space-4); }
.h5-stepper__step {
  flex: 1;
  position: relative;
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--color-text-3);
}
.h5-stepper__step::before {
  content: '';
  position: absolute;
  top: 9px;
  left: -50%;
  width: 100%;
  height: 2px;
  background: var(--color-border);
}
.h5-stepper__step:first-child::before { display: none; }
.h5-stepper__step.is-done::before { background: var(--color-accent); }
.h5-stepper__step i {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  margin: 0 auto var(--space-1);
  border-radius: 50%;
  border: 1.5px solid var(--color-border-strong);
  background: var(--color-surface);
  font-style: normal;
  font-size: 11px;
  position: relative;
  z-index: 1;
  color: var(--color-text-3);
}
.h5-stepper__step.is-on { color: var(--color-accent); font-weight: 500; }
.h5-stepper__step.is-on i,
.h5-stepper__step.is-done i {
  border-color: var(--color-accent);
  background: var(--color-accent);
  color: var(--color-surface);
}
</style>
