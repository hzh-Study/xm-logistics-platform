"""鉴权业务：口令校验、会话创建与撤销。"""

import sqlite3
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.core.security import (
    new_csrf_token,
    new_token,
    sha256_hex,
    verify_password,
)
from app.exceptions import AccountUnavailableError, AuthenticationError
from app.schemas.auth import UserOut

_ACCOUNT_COLUMNS = "id, phone, role, account_status, auth_status, password_hash"


def authenticate(conn: sqlite3.Connection, phone: str, password: str):
    """校验口令并返回账号行，失败抛领域异常。"""
    account = conn.execute(
        f"SELECT {_ACCOUNT_COLUMNS} FROM accounts WHERE phone = ?", (phone,)
    ).fetchone()
    if account is None or not verify_password(password, account["password_hash"]):
        raise AuthenticationError()
    if account["account_status"] != "正常使用":
        raise AccountUnavailableError()
    return account


def create_session(
    conn: sqlite3.Connection, account, settings: Settings
) -> tuple[str, str, UserOut]:
    """创建会话记录，返回 (token, csrf, 用户)。"""
    token = new_token()
    csrf = new_csrf_token()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=settings.session_ttl_seconds)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """INSERT INTO sessions
               (token_hash, account_id, role, csrf_token, expires_at, revoked_at, created_at)
               VALUES (?, ?, ?, ?, ?, NULL, ?)""",
            (
                sha256_hex(token),
                account["id"],
                account["role"],
                csrf,
                expires.isoformat(),
                now.isoformat(),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    user = UserOut(
        id=account["id"],
        phone=account["phone"],
        role=account["role"],
        account_status=account["account_status"],
        auth_status=account["auth_status"],
    )
    return token, csrf, user


def revoke_session(conn: sqlite3.Connection, token: str) -> None:
    """撤销当前 token 对应的会话。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (datetime.now(timezone.utc).isoformat(), sha256_hex(token)),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
