# Composable

适用范围：抽复用逻辑、写 `useX` 函数。

## 规则

- MUST 以 `use` 开头命名（如 `useOrderFilters`），返回普通对象（包裹 ref）。理由：与官方约定一致，一眼识别。
- MUST 让每次调用拿到独立实例——状态放在函数体内，不放模块顶层。理由：模块级单例跨调用方共享，测试与复用会互相污染。
- MUST 在 `setup` 中同步调用，MUST NOT 在异步回调里调用。理由：组合式 API 的上下文只在同步 setup 阶段可用。
- MUST 副作用放 `onMounted`，清理放 `onUnmounted`（监听、定时器、请求）。理由：避免内存泄漏。
- MUST 只封装「一段有状态逻辑 + 其副作用」，MUST NOT 把整个页面的业务塞进一个 composable。理由：保持单一职责、可组合。
- 判断顺序：单个组件本地状态用 `ref`；复用的有状态逻辑用 composable；跨无关组件共享、导航后仍存活、需 devtools 的状态用 Pinia（见 `state.md`）。理由：官方建议「拿不准先用 ref」，不过度抽象。
- MUST 由 composable 调用 `api/` 函数，MUST NOT 在组件里直接发请求（见 `api-request.md`）。理由：请求与组件解耦。
- MUST 给导出的 composable 写一行 JSDoc 说明其契约（见 `../comments/docstrings.md`）。理由：公开 API 需最小说明。

## Checklist

- [ ] `use` 前缀，返回 ref 对象
- [ ] 状态在函数体内，非模块单例
- [ ] 同步调用，副作用与清理成对
- [ ] 单一职责，请求经 `api/`
- [ ] 导出者有单行 JSDoc
