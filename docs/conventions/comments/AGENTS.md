# 注释规范索引

写任何注释前先读本文件，再**只读命中的那一个**类型文件。规则为强制（MUST / MUST NOT），附一行 rationale，文末有 checklist。跨前端 / 后端 / 数据库统一。

- 写行内说明注释、解释一段实现 → `inline.md`
- 写 TODO / FIX / HACK / NOTE 标记 → `markers.md`
- 写函数 / 类的 docstring 或 JSDoc → `docstrings.md`
- 写建表语句里的字段 / 表注释 → `schema-comments.md`

总原则：**短小、统一、说明「这是什么」**。注释正文用中文，标识符 / 标记 / 技术术语保留英文。
