# Vue 3 规范索引

写 Vue 3 代码前先读本文件，再**只读命中的那一个**类型文件。规则为强制（MUST / MUST NOT），附一行 rationale，文末有 checklist。

- 写或改 SFC 组件、props / emits、模板、组件命名 → `component.md`
- 抽复用逻辑、写 `useX` composable → `composable.md`
- 发请求、封装 API client、处理响应错误 → `api-request.md`
- 跨组件共享状态、用 Pinia store → `state.md`
- 加路由、守卫、按角色隔离视图 → `router.md`
- 写样式、CSS 变量、主题 → `style.md`

术语以仓库根 `GLOSSARY.md` 为准：运输订单 / 运输任务 / 货源 不可混用。
