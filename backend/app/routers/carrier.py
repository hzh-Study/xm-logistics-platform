"""物流公司路由：注册、企业认证与业务入口。"""

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

from app.dependencies import ActiveCarrierDep, CarrierDep, CsrfDep, DbConnection
from app.exceptions import PhoneAlreadyRegisteredError
from app.schemas.auth import UserOut
from app.schemas.carrier import (
    CarrierRegisterIn,
    CertificationRecordOut,
    CertificationSubmitIn,
    CertificationViewOut,
    BusinessAccessOut,
    CapabilitiesOut,
)
from app.services import carrier as carrier_service

router = APIRouter(prefix="/api/carrier", tags=["carrier"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: CarrierRegisterIn, conn: DbConnection) -> UserOut:
    """注册物流公司账号（公开入口，与登录同属会话前写操作）。"""
    try:
        return carrier_service.register_carrier(
            conn, payload.phone, payload.password, payload.company_name
        )
    except PhoneAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="手机号已被注册"
        )


@router.post(
    "/certification",
    response_model=CertificationRecordOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_certification(
    payload: CertificationSubmitIn,
    user: CarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> CertificationRecordOut:
    """提交或重新提交企业认证资料。"""
    return carrier_service.submit_certification(conn, user.id, payload)


@router.get("/certification", response_model=CertificationViewOut)
def get_certification(user: CarrierDep, conn: DbConnection) -> CertificationViewOut:
    """读取当前认证状态、最新结果与全部历史记录。"""
    return carrier_service.certification_view(conn, user.id)


@router.get("/capabilities", response_model=CapabilitiesOut)
def get_capabilities(user: CarrierDep, conn: DbConnection) -> CapabilitiesOut:
    """读取承运业务能力开关，供前端据认证与账号状态渲染。"""
    account = conn.execute(
        "SELECT account_status, auth_status FROM accounts WHERE id = ?", (user.id,)
    ).fetchone()
    return carrier_service.capabilities(
        account["account_status"], account["auth_status"]
    )


@router.get("/business-access", response_model=BusinessAccessOut)
def business_access(user: ActiveCarrierDep, conn: DbConnection) -> BusinessAccessOut:
    """承运业务统一入口：承接、派单、司机与车辆管理均经此门禁。"""
    account = conn.execute(
        "SELECT account_status, auth_status FROM accounts WHERE id = ?", (user.id,)
    ).fetchone()
    return BusinessAccessOut(
        company_name=carrier_service.company_name_of(conn, user.id),
        auth_status=account["auth_status"],
        capabilities=carrier_service.capabilities(
            account["account_status"], account["auth_status"]
        ),
    )
