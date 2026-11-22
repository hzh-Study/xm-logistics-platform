"""在途异常路由：司机上报，物流公司追加处理记录，三方只读查看。"""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import (
    ActiveCarrierDep,
    BoundDriverDep,
    CsrfDep,
    DbConnection,
    ShipperDep,
)
from app.exceptions import (
    DriverNotFoundError,
    ExceptionRuleError,
    TaskNotFoundError,
    VehicleNotAssignableError,
)
from app.schemas.exception import AnomalyIn, AnomalyOut, ExceptionViewOut, HandlingIn, HandlingOut
from app.services import exception as exception_service

driver_router = APIRouter(prefix="/api/driver/tasks", tags=["exception-driver"])
carrier_router = APIRouter(prefix="/api/carrier/tasks", tags=["exception-carrier"])
shipper_router = APIRouter(prefix="/api/shipper/orders", tags=["exception-shipper"])


def _rule(exc: ExceptionRuleError | VehicleNotAssignableError) -> HTTPException:
    """前置条件失败：409，具体原因进入错误信封。"""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


@driver_router.post(
    "/{task_id}/anomalies",
    response_model=AnomalyOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_anomaly(
    task_id: int,
    payload: AnomalyIn,
    user: BoundDriverDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> AnomalyOut:
    """司机提交在途异常与现场照片。"""
    try:
        return exception_service.submit_anomaly(conn, user.id, task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")
    except ExceptionRuleError as exc:
        raise _rule(exc)


@driver_router.get("/{task_id}/exceptions", response_model=ExceptionViewOut)
def driver_exceptions(
    task_id: int, user: BoundDriverDep, conn: DbConnection
) -> ExceptionViewOut:
    """司机读取本人任务的异常与处理记录。"""
    try:
        return exception_service.driver_exceptions(conn, user.id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")


@carrier_router.post(
    "/{task_id}/exceptions/{anomaly_id}/handle",
    response_model=HandlingOut,
    status_code=status.HTTP_201_CREATED,
)
def handle_anomaly(
    task_id: int,
    anomaly_id: int,
    payload: HandlingIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> HandlingOut:
    """物流公司追加异常处理记录，映射订单状态。"""
    try:
        return exception_service.handle_anomaly(conn, user.id, task_id, anomaly_id, payload)
    except (TaskNotFoundError, DriverNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务或异常不存在")
    except (ExceptionRuleError, VehicleNotAssignableError) as exc:
        raise _rule(exc)


@carrier_router.get("/{task_id}/exceptions", response_model=ExceptionViewOut)
def carrier_exceptions(
    task_id: int, user: ActiveCarrierDep, conn: DbConnection
) -> ExceptionViewOut:
    """物流公司读取本公司任务的异常与处理记录。"""
    try:
        return exception_service.carrier_exceptions(conn, user.id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输任务不存在")


@shipper_router.get("/{order_id}/exceptions", response_model=ExceptionViewOut)
def shipper_exceptions(
    order_id: int, user: ShipperDep, conn: DbConnection
) -> ExceptionViewOut:
    """货主只读查看自己订单上的异常与处理记录。"""
    try:
        return exception_service.shipper_exceptions(conn, user.id, order_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运输订单不存在")
