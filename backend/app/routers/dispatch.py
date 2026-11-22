"""派单路由：物流公司派单 / 重新派单 / 任务查询，司机确认 / 拒绝。"""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import ActiveCarrierDep, BoundDriverDep, CsrfDep, DbConnection
from app.exceptions import (
    DispatchRuleError,
    DriverNotFoundError,
    OrderNotFoundError,
    TaskNotFoundError,
    TaskStateError,
    VehicleNotAssignableError,
    VehicleNotFoundError,
)
from app.schemas.dispatch import (
    DispatchCreateIn,
    DispatchHistoryOut,
    DriverRejectIn,
    DriverTaskOut,
    RedispatchIn,
    TaskOut,
)
from app.schemas.shipper import NotificationOut, OrderOut
from app.services import dispatch as dispatch_service

carrier_router = APIRouter(prefix="/api/carrier", tags=["dispatch-carrier"])
driver_router = APIRouter(prefix="/api/driver", tags=["dispatch-driver"])


def _rule(exc: DispatchRuleError) -> HTTPException:
    """派单规则失败：409，原因进入错误信封。"""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


@carrier_router.get("/orders", response_model=list[OrderOut])
def list_orders(
    user: ActiveCarrierDep,
    conn: DbConnection,
    status_filter: str | None = None,
    order_no: str | None = None,
    cargo_name: str | None = None,
) -> list[OrderOut]:
    """物流公司列出自己承接的订单，供派单挑选。"""
    return dispatch_service.list_carrier_orders(
        conn, user.id, status_filter, order_no, cargo_name
    )


@carrier_router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: str, user: ActiveCarrierDep, conn: DbConnection) -> OrderOut:
    """物流公司读取自己承接的一条订单详情。"""
    if not order_id.isdigit():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输订单不存在")
    try:
        return dispatch_service.get_carrier_order(conn, user.id, int(order_id))
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输订单不存在")


@carrier_router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: DispatchCreateIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> TaskOut:
    """为已承接订单派单，创建运输任务并占用司机 / 车辆。"""
    try:
        return dispatch_service.create_dispatch(conn, user.id, payload)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输订单不存在")
    except DriverNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="司机不存在")
    except VehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆不存在")
    except VehicleNotAssignableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)
    except DispatchRuleError as exc:
        raise _rule(exc)


@carrier_router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    user: ActiveCarrierDep,
    conn: DbConnection,
    status_filter: str | None = None,
    order_id: int | None = None,
) -> list[TaskOut]:
    """物流公司列出本公司运输任务，可按状态 / 订单筛选。"""
    return dispatch_service.list_tasks(conn, user.id, status_filter, order_id)


@carrier_router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, user: ActiveCarrierDep, conn: DbConnection) -> TaskOut:
    """物流公司读取一条运输任务详情。"""
    try:
        return dispatch_service.get_task(conn, user.id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")


@carrier_router.get(
    "/tasks/{task_id}/dispatch-history", response_model=list[DispatchHistoryOut]
)
def get_dispatch_history(
    task_id: int, user: ActiveCarrierDep, conn: DbConnection
) -> list[DispatchHistoryOut]:
    """读取一条任务的派单历史，只读追加。"""
    try:
        return dispatch_service.task_dispatch_history(conn, user.id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")


@carrier_router.post("/tasks/{task_id}/redispatch", response_model=TaskOut)
def redispatch_task(
    task_id: int,
    payload: RedispatchIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> TaskOut:
    """未起运重新派单，记录原 / 新司机车辆与原因。"""
    try:
        return dispatch_service.redispatch(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except DriverNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="司机不存在")
    except VehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆不存在")
    except VehicleNotAssignableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)
    except TaskStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except DispatchRuleError as exc:
        raise _rule(exc)


@carrier_router.get("/notifications", response_model=list[NotificationOut])
def carrier_notifications(
    user: ActiveCarrierDep, conn: DbConnection
) -> list[NotificationOut]:
    """物流公司读取自己的站内通知。"""
    return dispatch_service.list_notifications(conn, user.id)


@driver_router.get("/tasks", response_model=list[DriverTaskOut])
def driver_tasks(user: BoundDriverDep, conn: DbConnection) -> list[DriverTaskOut]:
    """司机列出派给自己的运输任务。"""
    return dispatch_service.driver_tasks(conn, user.id)


@driver_router.get("/tasks/{task_id}", response_model=DriverTaskOut)
def driver_task(task_id: int, user: BoundDriverDep, conn: DbConnection) -> DriverTaskOut:
    """司机读取任务详情；出参不含运费报价。"""
    try:
        return dispatch_service.driver_task(conn, user.id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")


@driver_router.post("/tasks/{task_id}/accept", response_model=DriverTaskOut)
def accept_task(
    task_id: int, user: BoundDriverDep, conn: DbConnection, _csrf: CsrfDep
) -> DriverTaskOut:
    """司机确认任务，状态推进到待装货。"""
    try:
        return dispatch_service.driver_accept(conn, user.id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@driver_router.post("/tasks/{task_id}/reject", response_model=DriverTaskOut)
def reject_task(
    task_id: int,
    payload: DriverRejectIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> DriverTaskOut:
    """司机填写原因拒绝任务，任务转终态已拒绝。"""
    try:
        return dispatch_service.driver_reject(conn, user.id, task_id, payload.reason)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except TaskStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except DispatchRuleError as exc:
        raise _rule(exc)


@driver_router.get("/notifications", response_model=list[NotificationOut])
def driver_notifications(
    user: BoundDriverDep, conn: DbConnection
) -> list[NotificationOut]:
    """司机读取自己的站内通知。"""
    return dispatch_service.list_notifications(conn, user.id)
