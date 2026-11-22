# 表结构与迁移

适用范围：建表、改表、加索引、写迁移脚本。只用标准库 sqlite3。

## 规则

- MUST 用版本化 `.py` 迁移脚本，按顺序追加，MUST NOT 修改已发布的脚本。理由：升级路径可复现、可追溯。
- MUST 版本号存在 `PRAGMA user_version`，每步迁移 + 版本递增放在同一个 `BEGIN IMMEDIATE` 事务里，并在事务内读版本。理由：库始终处于某个已知版本，防并发重复迁移。
- MUST 遇到「库版本高于代码可识别版本」时拒绝打开。理由：防降级写坏数据。
- MUST 只允许追加式变更（`ALTER TABLE ... ADD COLUMN`），MUST NOT DROP / 重建历史表。理由：历史不可变（ADR-0004）。
- MUST 用 STRICT 表；状态机枚举用 `CHECK` 约束；引用历史的 FK 用显式 `ON DELETE/UPDATE RESTRICT`。理由：在 DB 层拒绝非法状态与误删。
- MUST 用 `UNIQUE`（或 `WHERE active=1` 的部分唯一索引）保证「一单仅一家物流公司承接」等唯一性。理由：并发下也守得住业务约束。
- MUST 为列表筛选的 WHERE / GROUP BY 列建复合索引；SQLite 无 INCLUDE，做覆盖索引时把查询列追加为尾部键列。理由：查询性能。
- MUST 金额存「分」的 INTEGER，时间在库内存 ISO 8601 TEXT。理由：整数无浮点误差、文本可按时间排序（见 `../fastapi/schema.md`）。
- MUST 字段注释用简短 `--` 行注释（见 `../comments/schema-comments.md`）。理由：自文档化。

## Checklist

- [ ] 版本化脚本不改旧的，`user_version` + 单事务
- [ ] 只追加变更，无 DROP / 重建历史
- [ ] STRICT + CHECK + FK RESTRICT + UNIQUE
- [ ] 复合索引、金额分、时间 ISO TEXT、字段注释
