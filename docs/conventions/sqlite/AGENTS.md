# SQLite 规范索引

碰数据库前先读本文件，再**只读命中的那一个**类型文件。规则为强制（MUST / MUST NOT），附一行 rationale，文末有 checklist。

- 建表、改表、写迁移、字段与索引设计 → `schema-migration.md`
- 写查询、拼接条件、排序、绑定参数 → `query.md`
- 拿连接、开事务、并发与 pragma → `transaction.md`
- 写追加式历史、不可变记录、更正留痕 → `append-only-history.md`

术语以仓库根 `GLOSSARY.md` 为准；历史不可变见 ADR-0004。
