# 数据库字段 / 表注释

适用范围：建表语句里的 `--` 注释。跨端统一，短。

## 规则

- MUST 用简短 `--` 行注释，紧贴字段或表定义。理由：与行内注释统一。
- MUST 注释内容 = 业务含义 + 枚举取值（如有）+ 单位（如有）。理由：让读表结构的人 / AI 一眼看懂。
- MUST 金额字段注明单位「分」、时间字段注明「ISO 8601」。理由：消除单位歧义。
- MUST NOT 给自解释字段写注释——如 `id`、`created_at`、按父表命名的外键（`order_id`）。理由：无信息量。
- MUST 枚举状态取值对齐需求文档与 `GLOSSARY.md`。理由：术语一致。
- MUST 与字段变更同更新。理由：防过时。

## 示例

```sql
status TEXT NOT NULL CHECK(status IN ('待承接','已承接','运输中','已完成','已取消')), -- 运输订单状态
amount_cents INTEGER NOT NULL, -- 金额，单位：分
created_at TEXT NOT NULL        -- 创建时间，ISO 8601
```

## Checklist

- [ ] `--` 行注释紧贴定义
- [ ] 业务含义 + 枚举 + 单位齐全
- [ ] 自解释字段不写，术语对齐 GLOSSARY
- [ ] 随字段变更同步
