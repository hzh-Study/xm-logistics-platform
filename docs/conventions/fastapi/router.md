# 路由层

适用范围：写 `app/routers/<domain>.py` 的路径操作。路由器只做 HTTP，不写业务。

## 规则

- MUST 每个业务域一个 `APIRouter`，路由函数保持「薄」：取参 → 调 service → 返回。理由：业务规则集中在 service，路由不可绕过鉴权 / 审计。
- MUST NOT 在路由函数里写 SQL 或业务判断。理由：分层，避免规则散落。
- MUST 每个响应显式声明 `response_model`（或返回类型），MUST NOT 返回裸 `dict`。理由：过滤掉不应暴露的字段（如运费对司机）。
- MUST 鉴权 / 当前用户 / 角色校验通过依赖注入获得（见 `dependency.md`），MUST NOT 在 handler 内重复判断。理由：单一来源，防遗漏。
- MUST 碰 sqlite3 的端点用同步 `def`，MUST NOT 用 `async def`。理由：sqlite3 是阻塞 I/O，同步函数走线程池，不阻塞事件循环。
- MUST 用明确的 HTTP 状态码（200 / 201 / 204 / 400 / 404 等），错误一律抛 `HTTPException`（见 `error.md`）。理由：语义清晰、错误统一。

## Checklist

- [ ] 路由薄，无 SQL / 业务判断
- [ ] 有 `response_model`，无裸 dict
- [ ] 鉴权走依赖，无重复判断
- [ ] 同步 `def`，状态码明确
