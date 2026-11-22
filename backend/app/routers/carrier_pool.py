"""物流公司订单池路由：货源浏览、筛选、详情与先到先得承接。"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import ActiveCarrierDep, CsrfDep, DbConnection
from app.exceptions import OrderNotAcceptableError, PoolOrderNotFoundError
from app.schemas.shipper import OrderOut
from app.services import carrier_pool

router = APIRouter(prefix="/api/carrier/order-pool", tags=["carrier-order-pool"])

_YUAN_PATTERN = r"^\d{1,9}(\.\d{1,2})?$"


@router.get("", response_model=list[OrderOut])
def list_pool(
    user: ActiveCarrierDep,
    conn: DbConnection,
    shipping_place: str | None = None,
    receiving_place: str | None = None,
    cargo_type: str | None = None,
    vehicle_type: str | None = None,
    weight: str | None = None,
    published_from: str | None = None,
    published_to: str | None = None,
    quote_min_yuan: Annotated[str | None, Query(pattern=_YUAN_PATTERN)] = None,
    quote_max_yuan: Annotated[str | None, Query(pattern=_YUAN_PATTERN)] = None,
) -> list[OrderOut]:
    """物流公司浏览公共订单池，可按发货地、收货地、类型、重量、发布时间与运费筛选。"""
    return carrier_pool.list_pool(
        conn,
        shipping_place,
        receiving_place,
        cargo_type,
        vehicle_type,
        weight,
        published_from,
        published_to,
        quote_min_yuan,
        quote_max_yuan,
    )


@router.get("/{order_id}", response_model=OrderOut)
def pool_detail(
    order_id: int,
    user: ActiveCarrierDep,
    conn: DbConnection,
) -> OrderOut:
    """物流公司查看一条待承接货源的完整详情。"""
    try:
        return carrier_pool.get_pool_detail(conn, order_id)
    except PoolOrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="货源不存在或已不在订单池")


@router.post("/{order_id}/accept", response_model=OrderOut)
def accept_order(
    order_id: int,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> OrderOut:
    """先到先得承接货源：成功后订单移出公共池并唯一归属当前物流公司。"""
    try:
        return carrier_pool.accept_order(conn, order_id, user.id)
    except PoolOrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="货源不存在或已不在订单池")
    except OrderNotAcceptableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
