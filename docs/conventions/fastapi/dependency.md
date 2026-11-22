# 依赖注入

适用范围：写 `app/dependencies.py` 的公共依赖与角色门禁。

## 规则

- MUST 用 `Annotated[..., Depends(fn)]` 并把常用依赖存成别名（`DbDep`、`CurrentUserDep`、`ShipperDep`、`CarrierDep`、`DriverDep`、`AdminDep`）。理由：跨路由复用且保留类型信息。
- MUST 数据库连接用 `yield` 依赖：`def get_db(): conn = ...; try: yield conn; finally: conn.close()`，`yield` 恰好一次，清理在 `finally`。理由：保证关闭，吞异常会产生难查的 500。
- MUST 鉴权链为：cookie 取 token → 查 session 哈希 → 解析 current_user → 角色门禁，逐层依赖。理由：单一链路、不重复。
- MUST 角色校验放在依赖 / service，MUST NOT 散落在各 handler。理由：防遗漏某条路由。
- MUST 捕获异常后原样抛出，MUST NOT 吞掉。理由：保留错误语义。
- MUST 被禁用账号在此链路即被拒绝（session 已标记撤销，见 `security.md`）。理由：禁用立即生效。

## Checklist

- [ ] `Annotated` + 依赖别名
- [ ] DB `yield` 依赖，`finally` 关闭
- [ ] 鉴权链分层，角色门禁集中
- [ ] 异常原样抛，禁用即时拒绝
