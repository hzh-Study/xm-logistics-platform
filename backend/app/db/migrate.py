"""版本化迁移：版本号存 user_version，迁移与递增在同一事务。"""

import sqlite3

LATEST_VERSION = 2

_SCHEMA = [
    """
    CREATE TABLE accounts (
        id             INTEGER PRIMARY KEY,
        phone          TEXT NOT NULL UNIQUE, -- 登录手机号
        role           TEXT NOT NULL CHECK(role IN ('货主','物流公司','司机','管理员')), -- 角色
        account_status TEXT NOT NULL CHECK(account_status IN ('正常使用','已禁用','已注销')), -- 账号状态
        auth_status    TEXT NOT NULL CHECK(auth_status IN ('未提交','待审核','审核通过','审核不通过')), -- 认证状态
        password_hash  TEXT NOT NULL,
        created_at     TEXT NOT NULL         -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE shipper_profiles (
        account_id   INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE RESTRICT,
        profile_type TEXT NOT NULL DEFAULT '' CHECK(profile_type IN ('','个人','企业')), -- 货主认证类型
        company_name TEXT NOT NULL DEFAULT ''
    ) STRICT
    """,
    """
    CREATE TABLE carrier_profiles (
        account_id   INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE RESTRICT,
        company_name TEXT NOT NULL DEFAULT '',
        license_no   TEXT NOT NULL DEFAULT ''
    ) STRICT
    """,
    """
    CREATE TABLE driver_profiles (
        account_id    INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE RESTRICT,
        carrier_id    INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 所属物流公司
        license_no    TEXT NOT NULL DEFAULT ''
    ) STRICT
    """,
    """
    CREATE TABLE admin_profiles (
        account_id   INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE RESTRICT,
        display_name TEXT NOT NULL DEFAULT ''
    ) STRICT
    """,
    """
    CREATE TABLE sessions (
        token_hash TEXT PRIMARY KEY,     -- token 的 SHA-256 摘要
        account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
        role       TEXT NOT NULL CHECK(role IN ('货主','物流公司','司机','管理员')),
        csrf_token TEXT NOT NULL,
        expires_at TEXT NOT NULL,        -- ISO 8601
        revoked_at TEXT,                 -- 撤销时间，ISO 8601
        created_at TEXT NOT NULL         -- ISO 8601
    ) STRICT
    """,
    "CREATE INDEX idx_sessions_account ON sessions(account_id)",
]

_PROFILE_TABLES = {
    "货主": "shipper_profiles",
    "物流公司": "carrier_profiles",
    "司机": "driver_profiles",
    "管理员": "admin_profiles",
}


def migrate(conn: sqlite3.Connection) -> None:
    """按版本顺序迁移到最新版本。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version > LATEST_VERSION:
            raise RuntimeError(f"库版本 {version} 高于代码可识别版本 {LATEST_VERSION}")
        if version < 1:
            for statement in _SCHEMA:
                conn.execute(statement)
            conn.execute("PRAGMA user_version = 1")
        if version < 2:
            from app.db.migrate_carrier import migrate_carrier

            migrate_carrier(conn)
            conn.execute("PRAGMA user_version = 2")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def profile_table_for(role: str) -> str:
    """返回角色对应的 profile 表名。"""
    return _PROFILE_TABLES[role]
