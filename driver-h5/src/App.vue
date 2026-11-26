<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
*, *::before, *::after { box-sizing: border-box; }

html, body { margin: 0; padding: 0; min-height: 100%; }

body {
  font-family: var(--font-sans);
  font-size: var(--font-size-md);
  line-height: var(--line-height);
  color: var(--color-text);
  background: var(--color-bg);
  -webkit-font-smoothing: antialiased;
}

/* Vant 主题对齐 design token */
:root {
  --van-primary-color: var(--color-accent);
  --van-success-color: var(--color-success);
  --van-warning-color: var(--color-warning);
  --van-danger-color: var(--color-error);
  --van-text-color: var(--color-text);
  --van-text-color-2: var(--color-text-2);
  --van-text-color-3: var(--color-text-3);
  --van-background-2: var(--color-surface);
  --van-background: var(--color-bg);
  --van-border-color: var(--color-border);
  --van-radius-lg: var(--radius-card);
  --van-font-size-md: var(--font-size-md);
  --van-cell-line-height: var(--line-height);
  --van-button-primary-background: var(--color-accent);
  --van-button-primary-border-color: var(--color-accent);
}

.h5-page {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 375px;
  min-height: 100vh;
  margin: 0 auto;
  background: var(--color-bg);
}
.h5-scroll {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3) var(--space-4) var(--space-6);
}
.h5-page--with-bar .h5-scroll { padding-bottom: calc(var(--space-12) + var(--safe-bottom)); }

.h5-section-title { margin: var(--space-4) 0 var(--space-2); font-size: var(--font-size-md); font-weight: 600; }
.h5-section-title:first-child { margin-top: 0; }
.h5-label { display: block; margin: var(--space-3) 0 var(--space-2); font-size: var(--font-size-sm); color: var(--color-text-2); font-weight: 500; }
.h5-label:first-child { margin-top: 0; }
.h5-req { color: var(--color-error); margin-right: 3px; }
.h5-help { margin: var(--space-1) 0 0; font-size: var(--font-size-xs); color: var(--color-text-3); }
.h5-error { margin: var(--space-1) 0 0; font-size: var(--font-size-xs); color: var(--color-error); }
.h5-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); padding: var(--space-2) 0; font-size: var(--font-size-md); }
.h5-row + .h5-row { border-top: 1px solid var(--color-border); }
.h5-row .k { color: var(--color-text-3); font-size: var(--font-size-sm); flex: 0 0 auto; }
.h5-row .v { text-align: right; min-width: 0; }
.h5-map {
  height: 108px;
  background: var(--color-fill);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--font-size-xs);
}
.h5-map svg { width: 28px; height: 28px; fill: none; stroke: currentColor; stroke-width: 1.2; }
.h5-timeline { position: relative; padding-left: var(--space-5); }
.h5-timeline::before { content: ''; position: absolute; left: 4px; top: 6px; bottom: 6px; width: 1px; background: var(--color-border); }
.h5-tl { position: relative; padding-bottom: var(--space-4); }
.h5-tl:last-child { padding-bottom: 0; }
.h5-tl::before { content: ''; position: absolute; left: -18px; top: 5px; width: 8px; height: 8px; border: 2px solid var(--color-border-strong); background: var(--color-surface); border-radius: 50%; }
.h5-tl.is-done::before { background: var(--color-accent); border-color: var(--color-accent); }
.h5-kv { display: grid; grid-template-columns: 76px 1fr; gap: var(--space-2) var(--space-3); font-size: var(--font-size-sm); }
.h5-kv dt { color: var(--color-text-3); }
.h5-kv dd { margin: 0; overflow-wrap: anywhere; }
.h5-num { font-variant-numeric: tabular-nums; text-align: right; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
</style>
