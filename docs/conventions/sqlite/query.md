# 查询与参数绑定

适用范围：写 SELECT / INSERT / UPDATE 与动态条件。安全第一。

## 规则

- MUST 所有用户输入经 `?`（qmark）或 `:name` 占位符绑定，MUST NOT 用 f-string / `%` / 拼接把值写进 SQL。理由：防 SQL 注入。
- MUST 动态 IN 列表按校验后的元素逐个生成 `?` 并绑定值；空列表短路返回空结果，大列表分批以避开参数上限。理由：值仍安全绑定，只拼出占位符与逗号。
- MUST 动态 ORDER BY 用「用户 token → 白名单列名 / 方向」的字典映射，MUST NOT 把用户文本拼进 SQL。理由：SQL 标识符无法参数化，只能白名单。
- MUST 转义 LIKE 中的 `%` / `_` 通配符。理由：防用户改变匹配语义。
- MUST 设 `row_factory = sqlite3.Row` 以列名取值。理由：可读、防列序错位。
- MUST 每条查询按当前主体 + 角色谓词约束（见 `../fastapi/security.md`）。理由：防越权读取。
- MUST NOT `SELECT *`，按需要列出字段。理由：避免误取敏感列（如运费）。

## Checklist

- [ ] 全部占位符绑定，无 f-string / 拼接值
- [ ] IN 逐个绑定、空列表短路、大列表分批
- [ ] ORDER BY 白名单，LIKE 转义通配符
- [ ] `row_factory=Row`，按主体约束，无 `SELECT *`
