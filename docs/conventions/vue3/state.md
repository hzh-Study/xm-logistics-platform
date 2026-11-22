# 状态管理（Pinia）

适用范围：跨组件共享状态、需要导航后存活或 devtools 可观测的状态。

## 规则

- MUST 按「本地 ref → composable → Pinia」顺序选择，能用前两者的不上 store。理由：最少全局状态，降低耦合。
- MUST 一个 store 一个文件，用 setup 语法（`defineStore('x', () => {...})`）。理由：与 `<script setup>` 风格一致、类型友好。
- MUST 用 `storeToRefs` 解构 state/getter，MUST NOT 直接解构 store 实例。理由：直接解构会丢失响应式。
- MUST 把登录态、当前用户、角色放进 auth store，角色视图的可见性由它驱动（见 `router.md`）。理由：权限单一来源。
- MUST NOT 在 store 里重复实现业务规则或发裸请求；业务经 service / api 层。理由：store 只管共享状态，不承载业务。
- MUST 金额在 store 内以「分」的整数保存，展示时才转「元」（见 `../sqlite/schema-migration.md`）。理由：避免浮点误差。
- MUST 给导出的 store 与 action 写一行 JSDoc（见 `../comments/docstrings.md`）。理由：公开契约最小说明。

## Checklist

- [ ] 确实需要跨组件 / 导航存活才用 store
- [ ] 一文件一 store，setup 语法
- [ ] `storeToRefs` 解构
- [ ] 登录态与角色在 auth store
- [ ] 金额按分存储，无裸请求
