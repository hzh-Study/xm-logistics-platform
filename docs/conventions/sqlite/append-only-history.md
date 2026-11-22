# 不可变历史

适用范围：订单历史、派单历史、车辆更换、打卡、费用、审核、异常处理记录。见 ADR-0004。

## 规则

- MUST 每条历史行带 `replaced_by`（指向替代它的新记录）、`reason`、`actor`、`created_at`（ISO 8601）。理由：更正可追溯、知道谁在何时为何改。
- MUST 更正是「插入一条新记录并让 `replaced_by` 指向旧记录」，MUST NOT UPDATE / DELETE 原记录。理由：历史只读、追加不可变。
- MUST 「当前有效」视图取 `replaced_by IS NULL` 的行。理由：无需覆盖原记录即可表达最新状态。
- MUST 历史表加 `BEFORE UPDATE` / `BEFORE DELETE` 触发器，`RAISE(ABORT, 'immutable history')`。理由：在 DB 层兜底阻止误改；不用 IGNORE（会静默吞掉写入）。
- MUST 主数据（仓库资料、司机基本资料）可改，业务历史不可改。理由：区分「可变主数据」与「不可变流水」。
- MUST 管理员的更正以追加「异常处理记录」完成，MUST NOT 直接改写订单 / 任务 / 打卡 / 费用。理由：保护证据（ADR-0004）。
- MUST 离职 / 转籍 / 停用等用状态字段表达，MUST NOT 物理删除。理由：引用不悬空、历史保留。

## Checklist

- [ ] 历史行有 replaced_by / reason / actor / created_at
- [ ] 更正靠追加，原记录不 UPDATE / DELETE
- [ ] 当前视图取 replaced_by IS NULL
- [ ] 有 BEFORE UPDATE/DELETE 的 ABORT 触发器
- [ ] 主数据可改、业务历史不可改，管理员追加留痕
