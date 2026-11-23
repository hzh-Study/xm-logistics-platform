"""种子数据：幂等创建平台管理员账号。"""

import sqlite3
from datetime import datetime

from app.core.security import hash_password
from app.db.migrate import profile_table_for


def seed_admin(conn: sqlite3.Connection, phone: str, password: str) -> None:
    """若手机号不存在且提供了口令，则创建管理员账号及其 profile。"""
    if not password:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        exists = conn.execute(
            "SELECT 1 FROM accounts WHERE phone = ?", (phone,)
        ).fetchone()
        if not exists:
            now = datetime.now().isoformat()
            cursor = conn.execute(
                """INSERT INTO accounts
                   (phone, role, account_status, auth_status, password_hash, created_at)
                   VALUES (?, '管理员', '正常使用', '审核通过', ?, ?)""",
                (phone, hash_password(password), now),
            )
            conn.execute(
                f"INSERT INTO {profile_table_for('管理员')} (account_id, display_name) VALUES (?, '平台管理员')",
                (cursor.lastrowid,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


_DEV_ADMIN_PHONE = "13800138000"
_DEV_CARRIER_PHONE = "13800138001"
_DEV_DRIVER_PHONE = "13800138002"


def _ensure_account(
    conn: sqlite3.Connection,
    phone: str,
    role: str,
    password: str,
    display_name: str,
) -> int:
    """确保账号存在并返回其 id，已存在时不覆盖口令。"""
    row = conn.execute("SELECT id FROM accounts WHERE phone = ?", (phone,)).fetchone()
    if row is not None:
        return row["id"]
    now = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO accounts
           (phone, role, account_status, auth_status, password_hash, created_at)
           VALUES (?, ?, '正常使用', '审核通过', ?, ?)""",
        (phone, role, hash_password(password), now),
    )
    account_id = cursor.lastrowid
    if role == "管理员":
        conn.execute(
            f"INSERT INTO {profile_table_for('管理员')} (account_id, display_name) VALUES (?, ?)",
            (account_id, display_name),
        )
    elif role == "物流公司":
        conn.execute(
            "INSERT INTO carrier_profiles (account_id, company_name, license_no) VALUES (?, ?, '')",
            (account_id, display_name),
        )
    return account_id


def seed_dev_accounts(conn: sqlite3.Connection, enabled: bool, password: str) -> None:
    """开发模式幂等创建管理员、物流公司与可直接进入工作台的司机账号。"""
    if not enabled or not password:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        _ensure_account(conn, _DEV_ADMIN_PHONE, "管理员", password, "平台管理员")
        carrier_id = _ensure_account(
            conn, _DEV_CARRIER_PHONE, "物流公司", password, "开发测试物流"
        )
        driver_id = _ensure_account(conn, _DEV_DRIVER_PHONE, "司机", password, "")
        conn.execute(
            """INSERT OR IGNORE INTO driver_profiles
               (account_id, carrier_id, must_change_password, binding_complete,
                employment, availability, qualification_status, name)
               VALUES (?, ?, 0, 1, '在职', '可派单', '有效', '测试司机')""",
            (driver_id, carrier_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
