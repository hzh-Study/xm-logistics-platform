# API 请求层

适用范围：封装 HTTP client、发请求、处理响应错误。后端契意见 `../fastapi/`。

## 规则

- MUST NOT 在组件或 composable 里直接用 `fetch` / axios。理由：统一入口才能统一鉴权与错误处理。
- MUST 全仓只有一个请求实例 `src/api/request.ts`，业务模块各建一个 `src/api/<domain>.ts`。理由：单一拦截点 + 按域组织。
- MUST baseURL 取 `import.meta.env.VITE_*`，MUST NOT 在 `VITE_*` 放任何密钥。理由：Vite 会把 `VITE_` 变量打包进客户端，密钥只能用后端持有。
- MUST 请求拦截器注入会话 cookie 所需的 `credentials` 与写操作的 `X-CSRF-Token`（见 `../fastapi/security.md`）。理由：与后端 cookie + CSRF 方案配套。
- MUST 响应拦截器把错误规范成后端统一信封 `{ error: { code, message, details } }` 对应的前端类型。理由：前端只认一种错误形状。
- MUST 用泛型 `request<T>()`，MUST NOT 返回裸 `any` / 未标注对象。理由：端到端类型安全。
- MUST 组件 → composable/store → `api/<domain>.ts`，禁止跨层直连。理由：分层隔离。
- MUST 给导出的请求函数写一行 JSDoc 说明用途（见 `../comments/docstrings.md`）。理由：公开 API 最小说明。

## Checklist

- [ ] 无组件内 `fetch`
- [ ] 单一 `request.ts`，按域分模块
- [ ] baseURL 走环境变量，无密钥
- [ ] 注入 CSRF，错误归一为信封
- [ ] 泛型返回类型，分层调用正确
