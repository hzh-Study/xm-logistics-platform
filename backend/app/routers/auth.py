"""鉴权路由：登录、当前用户、退出。"""

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import HTTPException

from app.config import Settings
from app.dependencies import CsrfDep, CurrentAccountDep, DbConnection
from app.exceptions import AccountUnavailableError, AuthenticationError
from app.core.security import session_cookie_name
from app.schemas.auth import LoginIn, LoginOut, MeOut, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    conn: DbConnection,
) -> LoginOut:
    """校验口令，下发会话 cookie 与 CSRF token。"""
    settings: Settings = request.app.state.settings
    try:
        account = auth_service.authenticate(conn, payload.phone, payload.password)
    except AuthenticationError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误")
    except AccountUnavailableError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不可用")
    token, csrf, user = auth_service.create_session(conn, account, settings)
    response.set_cookie(
        key=session_cookie_name(request),
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    return LoginOut(user=user, csrf_token=csrf)


@router.get("/me", response_model=MeOut)
def me(account: CurrentAccountDep) -> MeOut:
    """返回当前用户与会话 CSRF，供刷新后恢复。"""
    return MeOut(
        id=account["id"],
        phone=account["phone"],
        role=account["role"],
        account_status=account["account_status"],
        auth_status=account["auth_status"],
        csrf_token=account["csrf_token"],
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> Response:
    """撤销会话并清除 cookie。"""
    cookie_name = session_cookie_name(request)
    token = request.cookies.get(cookie_name)
    if token:
        auth_service.revoke_session(conn, token)
    response.delete_cookie(cookie_name, path="/")
    response.status_code = 204
    return response
