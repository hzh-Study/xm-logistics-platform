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
