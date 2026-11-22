<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--font-size-md);
  line-height: var(--line-height);
  color: var(--color-text);
  background: var(--color-bg);
}
</style>
