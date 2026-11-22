# 错误处理

适用范围：定义异常、注册处理器、控制跨角色可见性。

## 规则

- MUST 预期失败抛 `HTTPException`，并注册且只注册两个处理器：`StarletteHTTPException` 与 `RequestValidationError`。理由：覆盖全面且不重复。
- MUST 统一错误信封：`{"error": {"code": "...", "message": "...", "details": ...}}`。理由：前端只解析一种形状（见 `../vue3/api-request.md`）。
- MUST NOT 返回 `exc.errors()` / `exc.body` 原文、文件名、行号或堆栈。理由：`RequestValidationError` 含内部路径，会泄露实现。
- MUST 对「当前角色无权访问的对象」返回 404 而非 403 / 400。理由：不泄露对象存在性（OWASP BOLA）。
- MUST 驳回 / 校验失败的具体原因放进 `details`，MUST NOT 吞掉。理由：需求要求驳回原因可见。
- MUST 内部异常记录到日志，MUST NOT 把原始异常文本回给客户端。理由：排障与安全兼顾。

## Checklist

- [ ] 仅两个处理器，统一错误信封
- [ ] 无错误原文 / 文件名 / 堆栈回传
- [ ] 越权对象返回 404
- [ ] 驳回原因在 details，内部异常仅入日志
