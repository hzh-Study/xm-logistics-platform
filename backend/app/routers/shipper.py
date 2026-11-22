"""货主路由：注册、认证资料与状态、通知、订单发布门禁。"""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.config import Settings
from app.dependencies import CsrfDep, DbConnection, ShipperDep
from app.exceptions import (
    CertificationStateError,
    NotPublishableError,
    PhoneTakenError,
)
from app.schemas.auth import LoginOut
from app.schemas.shipper import (
    CertificationIn,
    CertificationOut,
    CertificationViewOut,
    NotificationOut,
    OrderOut,
    PublishIn,
    ShipperRegisterIn,
)
from app.services import auth as auth_service
from app.services import shipper as shipper_service

router = APIRouter(prefix="/api/shipper", tags=["shipper"])


@router.post("/register", response_model=LoginOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: ShipperRegisterIn,
    request: Request,
    response: Response,
    conn: DbConnection,
) -> LoginOut:
    """注册货主并下发会话 cookie 与 CSRF token。"""
    try:
        shipper_service.register_shipper(conn, payload.phone, payload.password)
    except PhoneTakenError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号已注册")
    settings: Settings = request.app.state.settings
    account = auth_service.authenticate(conn, payload.phone, payload.password)
    token, csrf, user = auth_service.create_session(conn, account, settings)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    return LoginOut(user=user, csrf_token=csrf)


@router.get("/certification", response_model=CertificationViewOut)
def read_certification(
    user: ShipperDep,
    conn: DbConnection,
) -> CertificationViewOut:
    """货主查看自己的认证状态与提交历史。"""
    return shipper_service.get_certification_view(conn, user.id, user.auth_status)


@router.post(
    "/certification",
    response_model=CertificationOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_certification(
    payload: CertificationIn,
    user: ShipperDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> CertificationOut:
    """货主提交个人 / 企业认证资料。"""
    try:
        return shipper_service.submit_certification(conn, user.id, payload)
    except CertificationStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    user: ShipperDep,
    conn: DbConnection,
) -> list[NotificationOut]:
    """货主查看发给自己的站内通知。"""
    return shipper_service.list_notifications(conn, user.id)


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def publish_order(
    payload: PublishIn,
    user: ShipperDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> OrderOut:
    """认证通过后发布运输订单。"""
    try:
        return shipper_service.publish_order(conn, user.id, payload.cargo_name)
    except NotPublishableError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    user: ShipperDep,
    conn: DbConnection,
) -> list[OrderOut]:
    """货主查看自己的运输订单。"""
    return shipper_service.list_orders(conn, user.id)

