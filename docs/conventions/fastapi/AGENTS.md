# FastAPI 规范索引

写后端代码前先读本文件，再**只读命中的那一个**类型文件。规则为强制（MUST / MUST NOT），附一行 rationale，文末有 checklist。

- 写或改路由、路径操作、状态码 → `router.md`
- 定义 Pydantic 入参 / 出参、字段约束、金额边界 → `schema.md`
- 写业务逻辑、组装服务、写不可变历史 → `service.md`
- 写依赖注入、登录态、角色校验 → `dependency.md`
- 定义错误、错误信封、跨角色可见性 → `error.md`
- 鉴权、CSRF、越权防护、CORS、密钥 → `security.md`

术语以仓库根 `GLOSSARY.md` 为准；架构边界见 `docs/adr/`。
