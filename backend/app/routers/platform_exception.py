"""管理员平台异常管理与车辆转籍路由：仅追加处理 / 转籍历史，不改写业务记录。"""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import AdminDep, CsrfDep, DbConnection
from app.exceptions import (
    AccountNotFoundError,
    OrderNotFoundError,
    PlatformExceptionNotFoundError,
    TaskNotFoundError,
    VehicleNotFoundError,
    VehicleTransferRuleError,
)
from app.schemas.platform_exception import (
    PlatformExceptionIn,
    PlatformExceptionOut,
    PlatformExceptionViewOut,
    PlatformHandlingIn,
    PlatformHandlingOut,
    VehicleTransferIn,
    VehicleTransferOut,
)
from app.services import platform_exception as platform_exception_service

router = APIRouter(prefix="/api/admin", tags=["admin-platform-exception"])

_NOT_FOUND_EXCEPTIONS = (
    AccountNotFoundError,
    OrderNotFoundError,
    TaskNotFoundError,
    VehicleNotFoundError,
)


@router.post(
    "/platform-exceptions",
    response_model=PlatformExceptionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_platform_exception(
    payload: PlatformExceptionIn,
    admin: AdminDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> PlatformExceptionOut:
    """管理员登记平台异常，作为追加处理记录的原始记录。"""
    try:
        return platform_exception_service.create_exception(conn, admin.id, payload)
    except _NOT_FOUND_EXCEPTIONS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="关联业务记录不存在")


@router.get("/platform-exceptions", response_model=list[PlatformExceptionOut])
def list_platform_exceptions(
    conn: DbConnection, _admin: AdminDep, category: str | None = None
) -> list[PlatformExceptionOut]:
    """按类别列出平台异常登记记录。"""
    return platform_exception_service.list_exceptions(conn, category)


@router.get("/platform-exceptions/{exception_id}", response_model=PlatformExceptionViewOut)
def get_platform_exception(
    exception_id: int, conn: DbConnection, _admin: AdminDep
) -> PlatformExceptionViewOut:
    """读取平台异常及全部追加处理记录。"""
    try:
        return platform_exception_service.get_exception(conn, exception_id)
    except PlatformExceptionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台异常记录不存在")


@router.post(
    "/platform-exceptions/{exception_id}/handling",
    response_model=PlatformHandlingOut,
    status_code=status.HTTP_201_CREATED,
)
def append_platform_handling(
    exception_id: int,
    payload: PlatformHandlingIn,
    admin: AdminDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> PlatformHandlingOut:
    """管理员追加异常处理记录，附 actor 角色、原因、结果与时间。"""
    try:
        return platform_exception_service.append_handling(conn, admin.id, exception_id, payload)
    except PlatformExceptionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台异常记录不存在")


@router.post(
    "/vehicle-transfers",
    response_model=VehicleTransferOut,
    status_code=status.HTTP_201_CREATED,
)
def transfer_vehicle(
    payload: VehicleTransferIn,
    admin: AdminDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> VehicleTransferOut:
    """车辆转籍：无进行中任务时放行并追加前后归属留痕，否则 409 说明原因。"""
    try:
        return platform_exception_service.transfer_vehicle(conn, admin.id, payload)
    except (VehicleNotFoundError, AccountNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆或转入物流公司不存在")
    except VehicleTransferRuleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


@router.get("/vehicle-transfers", response_model=list[VehicleTransferOut])
def list_vehicle_transfers(
    conn: DbConnection, _admin: AdminDep, vehicle_id: int | None = None
) -> list[VehicleTransferOut]:
    """列出转籍历史，可按车辆筛选。"""
    return platform_exception_service.list_transfers(conn, vehicle_id)
