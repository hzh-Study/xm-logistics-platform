"""订单取消路由：货主申请与查看，物流公司同意与驳回。"""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import ActiveCarrierDep, CsrfDep, DbConnection, ShipperDep
from app.exceptions import (
    CancelApplicationNotFoundError,
    CancelRuleError,
    OrderNotFoundError,
)
from app.schemas.cancel import (
    CancelApplyIn,
    CancelOptionsOut,
    CancelOut,
    CancelRejectIn,
    CancelViewOut,
)
from app.services import cancel as cancel_service

shipper_router = APIRouter(prefix="/api/shipper/orders", tags=["cancel-shipper"])
carrier_router = APIRouter(prefix="/api/carrier/cancel-applications", tags=["cancel-carrier"])


def _rule(exc: CancelRuleError) -> HTTPException:
    """前置条件失败：409，具体原因进入错误信封。"""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


@shipper_router.post(
    "/{order_id}/cancel",
    response_model=CancelOut,
    status_code=status.HTTP_201_CREATED,
)
def apply_cancel(
    order_id: int,
    payload: CancelApplyIn,
    user: ShipperDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> CancelOut:
    """货主按订单状态申请取消。"""
    try:
        return cancel_service.apply_cancel(conn, user.id, order_id, payload)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    except CancelRuleError as exc:
        raise _rule(exc)


@shipper_router.get("/{order_id}/cancel", response_model=CancelViewOut)
def cancellation_view(
    order_id: int, user: ShipperDep, conn: DbConnection
) -> CancelViewOut:
    """货主查看自己订单的取消申请与全过程留痕。"""
    try:
        return cancel_service.cancellation_view(conn, user.id, order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")


@shipper_router.get("/{order_id}/cancel-options", response_model=CancelOptionsOut)
def cancellation_options(
    order_id: int, user: ShipperDep, conn: DbConnection
) -> CancelOptionsOut:
    """货主读取订单是否提供取消入口及取消方式。"""
    try:
        return cancel_service.cancellation_options(conn, user.id, order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")


@carrier_router.get("", response_model=list[CancelOut])
def carrier_applications(
    user: ActiveCarrierDep, conn: DbConnection
) -> list[CancelOut]:
    """物流公司列出本公司承运订单上的取消申请。"""
    return cancel_service.carrier_applications(conn, user.id)


@carrier_router.get("/{application_id}", response_model=CancelViewOut)
def carrier_application_view(
    application_id: int, user: ActiveCarrierDep, conn: DbConnection
) -> CancelViewOut:
    """物流公司读取一条取消申请的当前态与留痕。"""
    try:
        return cancel_service.carrier_application_view(conn, user.id, application_id)
    except CancelApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="取消申请不存在"
        )


@carrier_router.post("/{application_id}/agree", response_model=CancelOut)
def agree_cancel(
    application_id: int,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> CancelOut:
    """物流公司同意取消申请。"""
    try:
        return cancel_service.agree_cancel(conn, user.id, application_id)
    except CancelApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="取消申请不存在"
        )
    except CancelRuleError as exc:
        raise _rule(exc)


@carrier_router.post("/{application_id}/reject", response_model=CancelOut)
def reject_cancel(
    application_id: int,
    payload: CancelRejectIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> CancelOut:
    """物流公司驳回取消申请，原因必填。"""
    try:
        return cancel_service.reject_cancel(conn, user.id, application_id, payload)
    except CancelApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="取消申请不存在"
        )
    except CancelRuleError as exc:
        raise _rule(exc)
