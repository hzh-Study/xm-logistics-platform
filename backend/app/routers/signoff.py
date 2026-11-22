"""签收路由：司机收货打卡/卸货/签收，公司确认，货主只读补录坐标。"""

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
    OrderNotFoundError,
    SignoffRuleError,
    TaskNotFoundError,
    TaskStateError,
)
from app.schemas.checkin import TaskProgressOut
from app.schemas.signoff import (
    ArrivalCheckinIn,
    ArrivalCheckinOut,
    ArrivalNoteIn,
    ArrivalNoteOut,
    ReceivingCoordinateIn,
    ReceivingCoordinateOut,
    SignoffConfirmIn,
    SignoffIn,
    UnloadingAnomalyIn,
    UnloadingAnomalyOut,
    UnloadingPhotosIn,
    UnloadingPhotosOut,
)
from app.services import signoff as signoff_service

driver_router = APIRouter(prefix="/api/driver/tasks", tags=["signoff-driver"])
carrier_router = APIRouter(prefix="/api/carrier/tasks", tags=["signoff-carrier"])
shipper_router = APIRouter(prefix="/api/shipper/orders", tags=["signoff-shipper"])


def _rule(exc: SignoffRuleError) -> HTTPException:
    """签收前置条件失败：409，具体原因进入错误信封。"""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


def _state(exc: TaskStateError) -> HTTPException:
    """任务状态冲突：409。"""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@driver_router.post(
    "/{task_id}/arrival-checkin",
    response_model=ArrivalCheckinOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_arrival_checkin(
    task_id: int,
    payload: ArrivalCheckinIn,
    user: BoundDriverDep,
    conn: DbConnection,
    radius_m: CheckinRadiusDep,
    _csrf: CsrfDep,
) -> ArrivalCheckinOut:
    """司机提交收货地打卡，超范围返回告警而非驳回。"""
    try:
        return signoff_service.submit_arrival_checkin(conn, user.id, task_id, payload, radius_m)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise _state(exc)


@driver_router.post(
    "/{task_id}/arrival-checkin/exception-note",
    response_model=ArrivalNoteOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_arrival_note(
    task_id: int,
    payload: ArrivalNoteIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> ArrivalNoteOut:
    """司机对收货地位置异常打卡补充说明。"""
    try:
        return signoff_service.submit_arrival_note(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except SignoffRuleError as exc:
        raise _rule(exc)


@driver_router.post(
    "/{task_id}/unloading/photos",
    response_model=UnloadingPhotosOut,
    status_code=status.HTTP_201_CREATED,
)
def add_unloading_photos(
    task_id: int,
    payload: UnloadingPhotosIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> UnloadingPhotosOut:
    """司机上传卸货前 / 中 / 完成照片。"""
    try:
        return signoff_service.add_unloading_photos(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise _state(exc)


@driver_router.post(
    "/{task_id}/unloading/anomalies",
    response_model=UnloadingAnomalyOut,
    status_code=status.HTTP_201_CREATED,
)
def add_unloading_anomaly(
    task_id: int,
    payload: UnloadingAnomalyIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> UnloadingAnomalyOut:
    """司机上报货损 / 数量不符 / 拒收等卸货异常。"""
    try:
        return signoff_service.add_unloading_anomaly(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise _state(exc)


@driver_router.post("/{task_id}/signoff", response_model=TaskProgressOut)
def submit_signoff(
    task_id: int,
    payload: SignoffIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> TaskProgressOut:
    """司机提交签收资料，签收凭证由公司据以确认完成。"""
    try:
        return signoff_service.submit_signoff(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise _state(exc)
    except SignoffRuleError as exc:
        raise _rule(exc)


@carrier_router.post("/{task_id}/signoff/confirm", response_model=TaskProgressOut)
def carrier_confirm(
    task_id: int,
    payload: SignoffConfirmIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> TaskProgressOut:
    """物流公司依据签收凭证确认任务完成，驱动订单完成。"""
    try:
        return signoff_service.carrier_confirm(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise _state(exc)
    except SignoffRuleError as exc:
        raise _rule(exc)


@shipper_router.post(
    "/{order_id}/receiving-coordinate", response_model=ReceivingCoordinateOut
)
def set_receiving_coordinate(
    order_id: int,
    payload: ReceivingCoordinateIn,
    user: ShipperDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> ReceivingCoordinateOut:
    """货主运输前补录收货快照坐标；完成后不可再改。"""
    try:
        return signoff_service.set_receiving_coordinate(conn, user.id, order_id, payload)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输订单不存在")
    except SignoffRuleError as exc:
        raise _rule(exc)
