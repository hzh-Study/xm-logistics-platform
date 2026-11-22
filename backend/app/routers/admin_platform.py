"""管理员平台路由：运营统计、全平台查询、统一审核、账号处置与公告发布。"""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import AdminDep, CsrfDep, DbConnection
from app.exceptions import (
    AccountNotFoundError,
    CarrierNotFoundError,
    CertificationNotFoundError,
    CertificationStateError,
    DriverNotFoundError,
    OrderNotFoundError,
    TaskNotFoundError,
)
from app.schemas.admin import (
    AccountStatusIn,
    AccountStatusOut,
    AdminStatsOut,
    AnnouncementIn,
    AnnouncementOut,
    CertItemOut,
    CertReviewOut,
    DriverSummaryOut,
    NoticeIn,
    NoticeOut,
    ShipperSummaryOut,
    UnifiedReviewIn,
    VehicleSummaryOut,
)
from app.schemas.dispatch import TaskOut
from app.schemas.shipper import OrderOut
from app.services import admin as admin_service

router = APIRouter(prefix="/api/admin", tags=["admin-platform"])


@router.get("/stats", response_model=AdminStatsOut)
def stats(conn: DbConnection, _admin: AdminDep) -> AdminStatsOut:
    """管理员首页运营统计。"""
    return admin_service.stats(conn)


@router.get("/shippers", response_model=list[ShipperSummaryOut])
def list_shippers(
    conn: DbConnection,
    _admin: AdminDep,
    company_name: str | None = None,
    auth_status: str | None = None,
) -> list[ShipperSummaryOut]:
    """查询全平台货主。"""
    return admin_service.list_shippers(conn, company_name, auth_status)


@router.get("/drivers", response_model=list[DriverSummaryOut])
def list_drivers(
    conn: DbConnection,
    _admin: AdminDep,
    driver_name: str | None = None,
    auth_status: str | None = None,
) -> list[DriverSummaryOut]:
    """查询全平台司机。"""
    return admin_service.list_drivers(conn, driver_name, auth_status)


@router.get("/vehicles", response_model=list[VehicleSummaryOut])
def list_vehicles(
    conn: DbConnection,
    _admin: AdminDep,
    plate_no: str | None = None,
    document_review_status: str | None = None,
) -> list[VehicleSummaryOut]:
    """查询全平台车辆。"""
    return admin_service.list_vehicles(conn, plate_no, document_review_status)


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    conn: DbConnection,
    _admin: AdminDep,
    order_no: str | None = None,
    shipper: str | None = None,
    company: str | None = None,
    status: str | None = None,
    published_from: str | None = None,
    published_to: str | None = None,
) -> list[OrderOut]:
    """按编号/货主/公司/状态/发布时间查询全平台运输订单。"""
    return admin_service.list_orders(
        conn, order_no, shipper, company, status, published_from, published_to
    )


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, conn: DbConnection, _admin: AdminDep) -> OrderOut:
    """读取任意运输订单详情。"""
    try:
        return admin_service.get_order(conn, order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输订单不存在")


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    conn: DbConnection,
    _admin: AdminDep,
    status: str | None = None,
    order_id: int | None = None,
    task_no: str | None = None,
    carrier_id: int | None = None,
    driver_id: int | None = None,
) -> list[TaskOut]:
    """查询全平台运输任务。"""
    return admin_service.list_tasks(conn, status, order_id, task_no, carrier_id, driver_id)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, conn: DbConnection, _admin: AdminDep) -> TaskOut:
    """读取任意运输任务详情。"""
    try:
        return admin_service.get_task(conn, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")


@router.get("/certifications", response_model=list[CertItemOut])
def list_certifications(
    conn: DbConnection,
    _admin: AdminDep,
    category: str | None = None,
    status: str | None = None,
) -> list[CertItemOut]:
    """五类认证的统一直观列表。"""
    return admin_service.list_certifications(conn, category, status)


@router.post("/certifications/review", response_model=CertReviewOut)
def review_certification(
    payload: UnifiedReviewIn,
    admin: AdminDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> CertReviewOut:
    """统一审核入口；驳回原因由入参模型强制必填。"""
    try:
        return admin_service.unified_review(conn, payload, admin.id)
    except (CertificationNotFoundError, CarrierNotFoundError, DriverNotFoundError, AccountNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="认证记录不存在")
    except CertificationStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/accounts/{account_id}/status", response_model=AccountStatusOut)
def set_account_status(
    account_id: int,
    payload: AccountStatusIn,
    conn: DbConnection,
    _admin: AdminDep,
    _csrf: CsrfDep,
) -> AccountStatusOut:
    """禁用或恢复业务账号，禁用时撤销其会话。"""
    try:
        return admin_service.set_account_status_unified(
            conn, account_id, payload.account_status
        )
    except AccountNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")


@router.post(
    "/announcements", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED
)
def publish_announcement(
    payload: AnnouncementIn,
    admin: AdminDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> AnnouncementOut:
    """发布平台公告，仅写公告表，不走业务事件通道。"""
    return admin_service.publish_announcement(conn, payload, admin.id)


@router.get("/announcements", response_model=list[AnnouncementOut])
def list_announcements(conn: DbConnection, _admin: AdminDep) -> list[AnnouncementOut]:
    """列出全部平台公告。"""
    return admin_service.list_announcements(conn)


@router.post("/notices", response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
def publish_notice(
    payload: NoticeIn,
    admin: AdminDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> NoticeOut:
    """发布平台通知，仅写通知表，不走业务事件通道。"""
    return admin_service.publish_notice(conn, payload, admin.id)


@router.get("/notices", response_model=list[NoticeOut])
def list_notices(conn: DbConnection, _admin: AdminDep) -> list[NoticeOut]:
    """列出全部平台通知。"""
    return admin_service.list_notices(conn)


# ---- 管理员对业务记录只读：写操作一律 403 ----------------------------------


def _readonly() -> None:
    """统一拒绝管理员改写业务记录。"""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="管理员对业务记录只读，禁止改写"
    )


@router.api_route(
    "/orders",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    response_model=None,
    include_in_schema=False,
)
def deny_order_collection_write(_admin: AdminDep) -> None:
    """拒绝管理员改写运输订单。"""
    _readonly()


@router.api_route(
    "/orders/{rest:path}",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    response_model=None,
    include_in_schema=False,
)
def deny_order_item_write(rest: str, _admin: AdminDep) -> None:
    """拒绝管理员改写单条运输订单。"""
    _readonly()


@router.api_route(
    "/tasks",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    response_model=None,
    include_in_schema=False,
)
def deny_task_collection_write(_admin: AdminDep) -> None:
    """拒绝管理员改写运输任务。"""
    _readonly()


@router.api_route(
    "/tasks/{rest:path}",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    response_model=None,
    include_in_schema=False,
)
def deny_task_item_write(rest: str, _admin: AdminDep) -> None:
    """拒绝管理员改写单条运输任务。"""
    _readonly()


@router.api_route(
    "/checkins",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    response_model=None,
    include_in_schema=False,
)
def deny_checkin_collection_write(_admin: AdminDep) -> None:
    """拒绝管理员改写打卡记录。"""
    _readonly()


@router.api_route(
    "/checkins/{rest:path}",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    response_model=None,
    include_in_schema=False,
)
def deny_checkin_item_write(rest: str, _admin: AdminDep) -> None:
    """拒绝管理员改写单条打卡记录。"""
    _readonly()


@router.api_route(
    "/expenses",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    response_model=None,
    include_in_schema=False,
)
def deny_expense_collection_write(_admin: AdminDep) -> None:
    """拒绝管理员改写报销费用。"""
    _readonly()


@router.api_route(
    "/expenses/{rest:path}",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    response_model=None,
    include_in_schema=False,
)
def deny_expense_item_write(rest: str, _admin: AdminDep) -> None:
    """拒绝管理员改写单条报销费用。"""
    _readonly()
