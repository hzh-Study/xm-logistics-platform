# SFC 组件

适用范围：写或改任何 `.vue` 组件（页面与通用组件）。

## 规则

- MUST 用 `<script setup lang="ts">`，不写 `<script>` 的 `export default defineComponent` 形式。理由：官方推荐，模板与响应式变量同域、样板最少。
- MUST 用纯类型声明 `defineProps<Props>()` 与 `defineEmits<{ (e: 'x', v: T): void }>()`。理由：类型即运行时校验，单一来源。
- MUST NOT 同时写运行时 props 声明和类型声明。理由：两者重复且易漂移，官方明确禁止。
- MUST 用 3.5 响应式解构取 props 默认值，MUST NOT 用 `withDefaults`。理由：`withDefaults` 是旧写法，已由响应式 props 解构取代。
- MUST 多词组件名（`OrderCard` 而非 `Card`），唯一例外是 `App.vue` 与路由级单根页面。理由：避免与原生 HTML 标签冲突。
- MUST 一文件一组件，文件名用 PascalCase 且与组件名一致。理由：定位与引用一致。
- MUST 给 `v-for` 配稳定的 `:key`，MUST NOT 把 `v-if` 与 `v-for` 写在同一个元素上。理由：官方 Priority A，避免渲染错乱；过滤应先算成新数组。
- MUST 模板只放简单表达式，复杂计算抽成 `computed`；MUST 用 `defineExpose` 作为组件唯一对外 API。理由：模板可读、对外面收窄。
- MUST 块顺序固定为 `<script setup>` → `<template>` → `<style scoped>`。理由：全仓统一，便于扫读（此为本地约定，非官方规则）。
- MUST 组件超过约 200 行或出现可复用逻辑时抽成 composable（见 `composable.md`）。理由：组件只负责编排。

## Checklist

- [ ] `<script setup lang="ts">`，无 `defineComponent`
- [ ] props / emits 为纯类型声明，未混运行时声明
- [ ] 多词命名、文件名 PascalCase、一文件一组件
- [ ] `v-for` 有稳定 key，`v-if`/`v-for` 不同元素
- [ ] 块顺序统一，复杂逻辑已抽离
