# 安全

适用范围：鉴权、CSRF、越权防护、CORS、密钥。硬约束，优先于便利。

## 规则

- MUST 用 opaque token（`secrets.token_urlsafe(32)`），经 httponly + Secure + SameSite=Lax cookie 下发；MUST NOT 用默认 JWT 流程。理由：JWT 只能靠 exp 失效，无法满足「禁用 / 退出立即失效」。
- MUST DB 只存 token 的 SHA-256 哈希 + user_id + role + expires_at + revoked_at；禁用 / 退出即标记 revoked。理由：即使库泄露也无法反推 token，且失效即时。
- MUST 所有写操作（POST / PUT / PATCH / DELETE）校验 `X-CSRF-Token` 头并核对 Origin；MUST NOT 在 GET 上做状态变更。理由：cookie 会被浏览器自动带上，SameSite 非充分防护（OWASP CSRF）。
- MUST 每条查询按「当前主体 + 角色谓词」约束，在数据层鉴权，MUST NOT 先取全表再在内存过滤。理由：OWASP BOLA 是 API 第一大风险；仅比较 session 用户 id 与参数 id 不够。
- MUST 用户输入只用 `?` / `:name` 绑定进 SQL（见 `../sqlite/query.md`）。理由：防 SQL 注入。
- MUST 响应固定 `Content-Type: application/json`，MUST NOT 把用户输入嵌进 HTML。理由：防 XSS。
- MUST CORS 显式列出两个前端来源 + `allow_credentials=True` + 明确 methods / headers，MUST NOT 用 `"*"` 配 credentials。理由：防跨站读取。
- MUST NOT 在代码 / 注释里写密钥、口令、主机地址。理由：防泄露。
- MUST 司机不可见运费报价；运费与报销费用是两条独立资金流（ADR-0007）。理由：权限与业务边界。

## Checklist

- [ ] opaque token + cookie 属性齐全，DB 存哈希
- [ ] 写操作校验 CSRF + Origin，GET 无副作用
- [ ] 查询按主体 + 角色约束，参数绑定
- [ ] JSON 响应、CORS 显式、无密钥、司机无运费
