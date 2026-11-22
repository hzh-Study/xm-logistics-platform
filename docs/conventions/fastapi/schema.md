# Pydantic 模型

适用范围：定义入参 / 出参模型与字段约束（Pydantic v2）。

## 规则

- MUST 每个入参模型设 `model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)`。理由：`forbid` 防批量赋值攻击，`strict` 防 `'123'` 被转成 `123`，去空格减少脏数据。
- MUST 用 `Field(min_length / max_length / ge / le / pattern)` 做约束，用 `Literal` / `Enum` 限定角色与状态取值。理由：校验在边界完成，非法状态进不来。
- MUST 入参 `XxxIn` 与出参 `XxxOut` 分离，MUST NOT 用同一个模型既收又发。理由：出参可剔除密码哈希、运费等敏感字段。
- MUST NOT 接受或返回裸 `dict`，MUST NOT 生成 Pydantic v1 的 `class Config`。理由：类型契约明确，v1 写法已废弃。
- MUST 金额在 API 边界用 Decimal 或「元」字符串表达，DB 层为「分」整数（见 `../sqlite/schema-migration.md`），转换只在边界发生。理由：对外可读、对内无浮点误差。
- MUST 状态字段取值严格对齐需求文档与 `GLOSSARY.md`（两套状态机不可混用）。理由：业务语义一致。

## Checklist

- [ ] `ConfigDict(extra="forbid", strict=True, ...)`
- [ ] Field 约束 + Literal/Enum，入出参分离
- [ ] 无裸 dict、无 v1 `class Config`
- [ ] 金额边界换算，状态取值对齐 GLOSSARY
