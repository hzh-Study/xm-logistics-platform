"""迁移完整性 guardrail：块顺序、各版本升级路径、快照不可变与禁用源码模式。

这是校验迁移改动的唯一规范命令（`cd backend && python -m pytest -q tests/test_migration_integrity.py`）。
它取代各合并子代理临时手写的 sanity 脚本——那些脚本曾因错误地 monkeypatch
LATEST_VERSION 而给出假阳性（守卫是字面量 `if version < N`，不受 LATEST_VERSION 影响）。
"""

import ast
import re
import sqlite3
from pathlib import Path

from app.db import migrate as migrate_module

_APP = Path(migrate_module.__file__).resolve().parent
_MIGRATE_PY = _APP / "migrate.py"
_LATEST = migrate_module.LATEST_VERSION


def _version_guards():
    """返回 (block_lineno, version_number)：migrate() 内的 `if version < N:` 守卫。"""
    tree = ast.parse(_MIGRATE_PY.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "migrate")
    guards = []
    for stmt in ast.walk(fn):
        if not isinstance(stmt, ast.If):
            continue
        test = stmt.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "version"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Lt)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and isinstance(test.comparators[0].value, int)
        ):
            guards.append((stmt.lineno, test.comparators[0].value))
    return guards


def _fresh_db(tmp_path, name="fresh.db"):
    conn = sqlite3.connect(tmp_path / name)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_up_to(conn, target: int) -> None:
    """在 conn 上执行到恰好 target 版本——用 AST 删除 >target 的守卫块后 exec。

    不用 monkeypatch LATEST_VERSION：守卫是字面量 `if version < N`，必须真正删块。
    """
    source = _MIGRATE_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "LATEST_VERSION" for t in node.targets
        ):
            node.value = ast.Constant(value=target)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "migrate")
    for stmt in ast.walk(fn):
        if isinstance(stmt, ast.Try):
            stmt.body = [
                s
                for s in stmt.body
                if not (
                    isinstance(s, ast.If)
                    and isinstance(s.test, ast.Compare)
                    and isinstance(s.test.left, ast.Name)
                    and s.test.left.id == "version"
                    and s.test.ops
                    and isinstance(s.test.ops[0], ast.Lt)
                    and isinstance(s.test.comparators[0], ast.Constant)
                    and s.test.comparators[0].value > target
                )
            ]
            break
    ast.fix_missing_locations(tree)
    namespace = {"__name__": "_migration_under_test"}
    exec(compile(tree, str(_MIGRATE_PY), "exec"), namespace)  # noqa: S102 - 本地受控源码
    namespace["migrate"](conn)


def test_guard_blocks_are_complete_ascending_and_set_matching_version():
    guards = _version_guards()
    numbers = [n for _, n in sorted(guards)]
    assert numbers == list(range(1, _LATEST + 1)), (
        f"迁移守卫必须是 1..{_LATEST} 严格升序且连续（无缺号/乱序/重复），实际为 {numbers}"
    )

    source = _MIGRATE_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "migrate")
    for stmt in ast.walk(fn):
        if not (isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare)):
            continue
        test = stmt.test
        if not (
            isinstance(test.left, ast.Name)
            and test.left.id == "version"
            and test.ops
            and isinstance(test.ops[0], ast.Lt)
            and isinstance(test.comparators[0], ast.Constant)
        ):
            continue
        expected = test.comparators[0].value
        sets = [
            c
            for c in ast.walk(stmt)
            if isinstance(c, ast.Call)
            and isinstance(c.func, ast.Attribute)
            and c.func.attr == "execute"
            and c.args
            and isinstance(c.args[0], ast.Constant)
            and isinstance(c.args[0].value, str)
            and f"PRAGMA user_version = {expected}" in c.args[0].value
        ]
        assert sets, f"v{expected} 块未设置 PRAGMA user_version = {expected}"


def test_every_migration_helper_module_is_referenced():
    """每个 migrate_<n>.py 都必须被 migrate() 引用，防止孤儿迁移模块静默不执行。"""
    source = _MIGRATE_PY.read_text(encoding="utf-8")
    referenced = set(re.findall(r"from\s+app\.db\.(migrate_\w+)\s+import", source))
    on_disk = {p.stem for p in _APP.glob("migrate_*.py")} - {"migrate"}
    assert on_disk <= referenced, (
        f"存在未被 migrate() 引用的迁移模块：{sorted(on_disk - referenced)}"
    )


def test_fresh_db_reaches_latest_and_is_idempotent(tmp_path):
    conn = _fresh_db(tmp_path)
    migrate_module.migrate(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == _LATEST
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"accounts", "orders", "transport_tasks", "warehouses", "vehicle_transfers"} <= tables
    migrate_module.migrate(conn)  # 幂等重跑
    assert conn.execute("PRAGMA user_version").fetchone()[0] == _LATEST
    conn.close()


def test_every_intermediate_version_upgrades_to_latest(tmp_path):
    for n in range(1, _LATEST):
        conn = _fresh_db(tmp_path, f"v{n}.db")
        _migrate_up_to(conn, n)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == n, f"无法构造真实的 v{n} 库"
        migrate_module.migrate(conn)  # 真实升级 N -> LATEST
        assert conn.execute("PRAGMA user_version").fetchone()[0] == _LATEST, f"v{n} 升级失败"
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", f"v{n} 升级后完整性失败"
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"accounts", "orders", "transport_tasks", "warehouses"} <= tables, f"v{n} 升级后缺表"
        conn.close()


def test_snapshot_trigger_aborts_snapshot_write_but_allows_status(tmp_path):
    conn = _fresh_db(tmp_path, "snap.db")
    migrate_module.migrate(conn)
    conn.execute(
        "INSERT INTO accounts (phone, role, account_status, auth_status, password_hash, created_at) "
        "VALUES ('13900000000', '货主', '正常使用', '审核通过', 'h', '2026-01-01T00:00:00')"
    )
    shipper_id = conn.execute("SELECT id FROM accounts").fetchone()[0]
    conn.execute(
        "INSERT INTO orders (order_no, shipper_id, cargo_name, status, created_at) "
        "VALUES ('ORD-260101-0001', ?, '货', '待承接', '2026-01-01T00:00:00')",
        (shipper_id,),
    )
    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE orders SET ship_name = '改名' WHERE id = 1")
    conn.execute("UPDATE orders SET status = '运输中' WHERE id = 1")  # 非快照列允许
    assert conn.execute("SELECT status FROM orders WHERE id = 1").fetchone()[0] == "运输中"
    conn.close()


def test_no_banned_source_patterns():
    banned = [
        (re.compile(r"SELECT\s+\*", re.I), "SELECT * (docs/conventions/sqlite/query.md)"),
        (re.compile(r"datetime\.utcnow\s*\("), "datetime.utcnow() (需要本地 ISO 8601)"),
        (re.compile(r"datetime\.now\s*\(\s*timezone\.utc"), "datetime.now(timezone.utc) (需要本地 ISO 8601)"),
    ]
    offenders = []
    for path in sorted(_APP.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            for pattern, label in banned:
                if pattern.search(line):
                    offenders.append(f"{path.relative_to(_APP.parent)}:{lineno}: {label}")
    assert not offenders, "发现禁用模式：\n" + "\n".join(offenders)
