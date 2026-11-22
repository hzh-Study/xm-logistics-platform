"""打卡路由：司机打卡/装货/起运，公司与货主查看进度。"""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import (
    ActiveCarrierDep,
    BoundDriverDep,
    CheckinRadiusDep,
    CsrfDep,
    DbConnection,
    ShipperDep,
)
from app.exceptions import (
    CheckinRuleError,
    OrderNotFoundError,
    TaskNotFoundError,
    TaskStateError,
)
from app.schemas.checkin import (
    CheckinIn,
    CheckinOut,
    ExceptionNoteIn,
    ExceptionNoteOut,
    LoadingAnomalyIn,
    LoadingAnomalyOut,
    LoadingPhotosIn,
    LoadingPhotosOut,
    SiteCoordinateIn,
    SiteCoordinateOut,
    StartTransportIn,
    TaskProgressOut,
)
from app.services import checkin as checkin_service

driver_router = APIRouter(prefix="/api/driver/tasks", tags=["checkin-driver"])
carrier_router = APIRouter(prefix="/api/carrier/tasks", tags=["checkin-carrier"])
shipper_router = APIRouter(prefix="/api/shipper/orders", tags=["checkin-shipper"])


def _rule(exc: CheckinRuleError) -> HTTPException:
    """打卡前置条件失败：409，具体原因进入错误信封。"""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


def _state(exc: TaskStateError) -> HTTPException:
    """任务状态冲突：409。"""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@driver_router.post("/{task_id}/checkin", response_model=CheckinOut, status_code=status.HTTP_201_CREATED)
def submit_checkin(
    task_id: int,
    payload: CheckinIn,
    user: BoundDriverDep,
    conn: DbConnection,
    radius_m: CheckinRadiusDep,
    _csrf: CsrfDep,
) -> CheckinOut:
    """司机提交发货地打卡，超范围返回告警而非驳回。"""
    try:
        return checkin_service.submit_checkin(conn, user.id, task_id, payload, radius_m)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise _state(exc)


@driver_router.post(
    "/{task_id}/checkin/exception-note",
    response_model=ExceptionNoteOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_exception_note(
    task_id: int,
    payload: ExceptionNoteIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> ExceptionNoteOut:
    """司机对位置异常打卡补充说明。"""
    try:
        return checkin_service.submit_exception_note(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except CheckinRuleError as exc:
        raise _rule(exc)


@driver_router.post(
    "/{task_id}/loading/photos",
    response_model=LoadingPhotosOut,
    status_code=status.HTTP_201_CREATED,
)
def add_loading_photos(
    task_id: int,
    payload: LoadingPhotosIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> LoadingPhotosOut:
    """司机上传装货前 / 中 / 完成照片。"""
    try:
        return checkin_service.add_loading_photos(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise _state(exc)


@driver_router.post(
    "/{task_id}/loading/anomalies",
    response_model=LoadingAnomalyOut,
    status_code=status.HTTP_201_CREATED,
)
def add_loading_anomaly(
    task_id: int,
    payload: LoadingAnomalyIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> LoadingAnomalyOut:
    """司机上报数量不符 / 货损 / 超载等装货异常。"""
    try:
        return checkin_service.add_loading_anomaly(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise _state(exc)


@driver_router.post("/{task_id}/start-transport", response_model=TaskProgressOut)
def start_transport(
    task_id: int,
    payload: StartTransportIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> TaskProgressOut:
    """起运前校验打卡、装货与核对确认，推进任务与订单状态。"""
    try:
        return checkin_service.start_transport(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise _state(exc)
    except CheckinRuleError as exc:
        raise _rule(exc)


@driver_router.get("/{task_id}/progress", response_model=TaskProgressOut)
def driver_progress(
    task_id: int, user: BoundDriverDep, conn: DbConnection
) -> TaskProgressOut:
    """司机读取本人任务进度，不含运费报价。"""
    try:
        return checkin_service.driver_progress(conn, user.id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")


@carrier_router.get("/{task_id}/progress", response_model=TaskProgressOut)
def carrier_progress(
    task_id: int, user: ActiveCarrierDep, conn: DbConnection
) -> TaskProgressOut:
    """物流公司查看本公司任务的打卡与装货进度。"""
    try:
        return checkin_service.carrier_progress(conn, user.id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")


@shipper_router.post("/{order_id}/site-coordinate", response_model=SiteCoordinateOut)
def set_site_coordinate(
    order_id: int,
    payload: SiteCoordinateIn,
    user: ShipperDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> SiteCoordinateOut:
    """货主起运前补录发货快照坐标。"""
    try:
        return checkin_service.set_site_coordinate(conn, user.id, order_id, payload)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输订单不存在")
    except CheckinRuleError as exc:
        raise _rule(exc)


@shipper_router.get("/{order_id}/progress", response_model=TaskProgressOut)
def shipper_progress(
    order_id: int, user: ShipperDep, conn: DbConnection
) -> TaskProgressOut:
    """货主只读查看自己订单的运输进度。"""
    try:
        return checkin_service.shipper_progress(conn, user.id, order_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
