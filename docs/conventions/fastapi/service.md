# 服务层

适用范围：写 `app/services/<domain>.py`，承载业务规则与不可变历史。

## 规则

- MUST 业务规则（承接唯一性、派单校验、取消分支、异常状态映射、费用审核）只写在 service。理由：规则单一来源，路由与定时任务都复用同一份。
- MUST service 不 import HTTP 层对象（`Request` / `Response` / `HTTPException`）；失败时抛领域异常，由路由 / 错误处理器转成 HTTP 响应（见 `error.md`）。理由：业务与传输解耦。
- MUST 所有对业务历史表的写入以「追加一条新记录」完成，MUST NOT UPDATE / DELETE 原记录（见 `../sqlite/append-only-history.md`、ADR-0004）。理由：历史只读不可变。
- MUST 多语句写入放进一个事务，`BEGIN IMMEDIATE` 开始，成功 commit、异常 rollback（见 `../sqlite/transaction.md`）。理由：不留半成品。
- MUST 每个 service 函数只做一件事，跨函数复用靠组合。理由：可测试、可维护。
- MUST NOT 把「禁用 / 审核 / 异常处置」写成对业务实体的直接改写；管理员写操作限定为审核、禁用 / 恢复、异常处理记录、公告。理由：保护证据（ADR-0004）。

## Checklist

- [ ] 业务规则集中，无 HTTP 对象
- [ ] 历史追加写，原记录不 UPDATE / DELETE
- [ ] 多语句一个事务
- [ ] 管理员写操作符合 ADR-0004 边界
