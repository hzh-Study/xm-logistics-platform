"""公共依赖：DB 连接、当前用户解析、角色门禁、CSRF 校验。"""

import hmac
import sqlite3
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.security import sha256_hex
from app.db.connection import connect
from app.schemas.auth import UserOut

_ACCOUNT_COLUMNS = "a.id, a.phone, a.role, a.account_status, a.auth_status"


def get_db(request: Request):
    """每请求一个连接，finally 关闭。"""
    conn = connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


DbConnection = Annotated[sqlite3.Connection, Depends(get_db)]


def _current_account(
    request: Request, conn: Annotated[sqlite3.Connection, Depends(get_db)]
) -> sqlite3.Row:
    """按 cookie token 解析有效会话与当前账号。"""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute(
        f"""SELECT {_ACCOUNT_COLUMNS}, s.csrf_token, s.expires_at
            FROM sessions s JOIN accounts a ON a.id = s.account_id
            WHERE s.token_hash = ? AND s.revoked_at IS NULL AND s.expires_at > ?""",
        (sha256_hex(token), now),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="会话无效")
    if row["account_status"] != "正常使用":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不可用")
    return row


def get_current_user(
    account: Annotated[sqlite3.Row, Depends(_current_account)],
) -> UserOut:
    """返回当前用户的公开信息。"""
    return UserOut(
        id=account["id"],
        phone=account["phone"],
        role=account["role"],
        account_status=account["account_status"],
        auth_status=account["auth_status"],
    )


CurrentUserDep = Annotated[UserOut, Depends(get_current_user)]
CurrentAccountDep = Annotated[sqlite3.Row, Depends(_current_account)]


def _require_role(*roles: str):
    """构造角色门禁依赖：仅允许给定角色。"""
    def gate(user: CurrentUserDep) -> UserOut:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")
        return user

    return gate


ShipperDep = Annotated[UserOut, Depends(_require_role("货主"))]
CarrierDep = Annotated[UserOut, Depends(_require_role("物流公司"))]
DriverDep = Annotated[UserOut, Depends(_require_role("司机"))]
AdminDep = Annotated[UserOut, Depends(_require_role("管理员"))]


def verify_csrf(
    request: Request,
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
) -> None:
    """写操作校验 CSRF token 与 Origin。"""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    now = datetime.now(timezone.utc).isoformat()
    session = conn.execute(
        """SELECT csrf_token FROM sessions
           WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?""",
        (sha256_hex(token), now),
    ).fetchone()
    supplied = request.headers.get("X-CSRF-Token")
    if session is None or not supplied or not hmac.compare_digest(supplied, session["csrf_token"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF 校验失败")
    origin = request.headers.get("origin")
    if origin and not _origin_allowed(origin, request.app.state.settings.cors_origins):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="来源不被允许")


def _origin_allowed(origin: str, allowed: tuple[str, ...]) -> bool:
    """校验 Origin 是否在允许来源内。"""
    return any(origin.rstrip("/") == item.rstrip("/") for item in allowed)


CsrfDep = Annotated[None, Depends(verify_csrf)]


def require_active_carrier(account: CurrentAccountDep) -> UserOut:
    """承运业务门禁：账号正常且企业认证审核通过才放行。"""
    if account["role"] != "物流公司":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")
    if account["account_status"] != "正常使用":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    if account["auth_status"] != "审核通过":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="企业认证未审核通过，无法承接订单或派单",
        )
    return get_current_user(account)


ActiveCarrierDep = Annotated[UserOut, Depends(require_active_carrier)]


def require_bound_driver(
    account: CurrentAccountDep,
    conn: Annotated[sqlite3.Connection, Depends(get_db)],
) -> UserOut:
    """司机工作台门禁：已改密、完成身份绑定、在职且所属公司正常。"""
    if account["role"] != "司机":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")
    from app.services.driver import onboarding

    state = onboarding(conn, account["id"])
    if state.blocked_reason:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=state.blocked_reason)
    return get_current_user(account)


BoundDriverDep = Annotated[UserOut, Depends(require_bound_driver)]
