"""司机路由：公司侧司机管理与司机侧首次登录绑定。"""

from typing import Literal

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

from app.dependencies import (
    ActiveCarrierDep,
    BoundDriverDep,
    CsrfDep,
    DbConnection,
    DriverDep,
)
from app.exceptions import (
    DriverBindingOrderError,
    DriverNotFoundError,
    PhoneAlreadyRegisteredError,
)
from app.schemas.driver import (
    AvailabilityIn,
    ChangePasswordIn,
    DriverAccountStatusIn,
    DriverBindingIn,
    DriverCreateIn,
    DriverIdentityRecord,
    DriverOut,
    DriverSelfOut,
    DriverUpdateIn,
    EmploymentIn,
    OnboardingOut,
)
from app.services import driver as driver_service

carrier_router = APIRouter(prefix="/api/carrier", tags=["carrier"])
driver_router = APIRouter(prefix="/api/driver", tags=["driver"])


@carrier_router.post("/drivers", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(
    payload: DriverCreateIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> DriverOut:
    """物流公司创建归属本公司的司机账号。"""
    try:
        return driver_service.create_driver(conn, user.id, payload)
    except PhoneAlreadyRegisteredError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号已被注册")


@carrier_router.get("/drivers", response_model=list[DriverOut])
def list_drivers(
    user: ActiveCarrierDep,
    conn: DbConnection,
    availability: Literal["可派单", "任务占用中", "暂停接单"] | None = None,
    employment: Literal["在职", "离职"] | None = None,
    account_status: Literal["正常使用", "已禁用"] | None = None,
) -> list[DriverOut]:
    """列出本公司司机，可按三类独立状态筛选。"""
    return driver_service.list_drivers(
        conn, user.id, availability, employment, account_status
    )


@carrier_router.get("/drivers/{account_id}", response_model=DriverOut)
def get_driver(
    account_id: int, user: ActiveCarrierDep, conn: DbConnection
) -> DriverOut:
    """读取一名本公司司机的完整资料。"""
    try:
        return driver_service.get_driver(conn, user.id, account_id)
    except DriverNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="司机不存在")


@carrier_router.put("/drivers/{account_id}", response_model=DriverOut)
def update_driver(
    account_id: int,
    payload: DriverUpdateIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> DriverOut:
    """修改司机基本资料；身份变更追加历史并触发重新审核。"""
    try:
        return driver_service.update_driver(conn, user.id, account_id, payload)
    except DriverNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="司机不存在")


@carrier_router.post("/drivers/{account_id}/availability", response_model=DriverOut)
def set_availability(
    account_id: int,
    payload: AvailabilityIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> DriverOut:
    """设置接单可用性，不影响在途任务。"""
    try:
        return driver_service.set_availability(
            conn, user.id, account_id, payload.availability
        )
    except DriverNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="司机不存在")


@carrier_router.post("/drivers/{account_id}/employment", response_model=DriverOut)
def set_employment(
    account_id: int,
    payload: EmploymentIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> DriverOut:
    """设置雇佣关系；离职同时禁用账号并撤销会话。"""
    try:
        return driver_service.set_employment(
            conn, user.id, account_id, payload.employment
        )
    except DriverNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="司机不存在")


@carrier_router.post("/drivers/{account_id}/account-status", response_model=DriverOut)
def set_account_status(
    account_id: int,
    payload: DriverAccountStatusIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> DriverOut:
    """设置司机账号状态，不改写另外两类状态。"""
    try:
        return driver_service.set_account_status(
            conn, user.id, account_id, payload.account_status
        )
    except DriverNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="司机不存在")


@carrier_router.get(
    "/drivers/{account_id}/identity-history", response_model=list[DriverIdentityRecord]
)
def get_identity_history(
    account_id: int, user: ActiveCarrierDep, conn: DbConnection
) -> list[DriverIdentityRecord]:
    """读取司机身份与驾驶资格提交历史（只读追加）。"""
    try:
        return driver_service.identity_history(conn, user.id, account_id)
    except DriverNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="司机不存在")


@driver_router.get("/onboarding", response_model=OnboardingOut)
def get_onboarding(user: DriverDep, conn: DbConnection) -> OnboardingOut:
    """读取司机首次登录强制改密与身份绑定的当前状态。"""
    return driver_service.onboarding(conn, user.id)


@driver_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordIn,
    user: DriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> None:
    """修改初始密码并清除强制改密标记。"""
    driver_service.change_password(conn, user.id, payload)
    return None


@driver_router.post("/binding", response_model=DriverSelfOut)
def bind_identity(
    payload: DriverBindingIn,
    user: DriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> DriverSelfOut:
    """补全身份与驾驶资格资料完成身份绑定。"""
    try:
        return driver_service.bind_identity(conn, user.id, payload)
    except DriverBindingOrderError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="请先修改初始密码"
        )


@driver_router.get("/workspace", response_model=DriverSelfOut)
def workspace(user: BoundDriverDep, conn: DbConnection) -> DriverSelfOut:
    """司机工作台入口：通过门禁后才返回自身资料。"""
    return driver_service.workspace(conn, user.id)
