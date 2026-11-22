# 路由与角色隔离

适用范围：加路由、导航守卫、按角色隔离视图。四类角色共用 Web 入口，司机端为 H5。

## 规则

- MUST 用 `meta: { requiresAuth, roles }` 描述权限，并用 `declare module 'vue-router'` 扩充 `RouteMeta` 类型。理由：类型化的路由元信息，拼错即编译报错。
- MUST 只有一个全局 `beforeEach`，MUST NOT 在各路由重复写权限判断。理由：守卫单一来源，避免遗漏。
- MUST 守卫里返回值（`return { name, query: { redirect } }`），MUST NOT 调用已废弃的 `next`。理由：Vue Router 4 起 `next` 已废弃。
- MUST 每个角色只能加载自己的视图树，无权限角色连组件都不加载。理由：越权不仅隐藏入口，还不能下载到视图代码。
- MUST `beforeEnter` 只放单路由专属规则，`onBeforeRouteLeave` 用于未保存编辑的离开确认。理由：职责分明。
- MUST 守卫保持「薄」，权限判断委托给 auth store。理由：业务规则不散落在路由层。
- MUST 按角色懒加载视图（动态 `import`）。理由：减小首包，配合隔离。

## Checklist

- [ ] `meta` 类型化，单一 `beforeEach`
- [ ] 守卫用返回值，无 `next`
- [ ] 角色视图隔离且不加载越权组件
- [ ] 权限委托 auth store，视图懒加载
