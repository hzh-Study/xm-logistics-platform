"""货主仓库路由：列表、搜索、创建、修改与状态流转。"""

from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi import status as http_status

from app.dependencies import CsrfDep, DbConnection, ShipperDep
from app.exceptions import WarehouseNotFoundError
from app.schemas.warehouse import WarehouseIn, WarehouseOut
from app.services import warehouse as warehouse_service

router = APIRouter(prefix="/api/shipper/warehouses", tags=["warehouse"])


@router.get("", response_model=list[WarehouseOut])
def list_warehouses(
    user: ShipperDep,
    conn: DbConnection,
    name: str | None = None,
    status: Literal["正常", "停用"] | None = None,
) -> list[WarehouseOut]:
    """货主查看自己的仓库，可按名称搜索与状态筛选。"""
    return warehouse_service.list_warehouses(conn, user.id, name, status)


@router.post("", response_model=WarehouseOut, status_code=http_status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseIn,
    user: ShipperDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> WarehouseOut:
    """货主新增仓库。"""
    return warehouse_service.create_warehouse(conn, user.id, payload)


@router.put("/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(
    warehouse_id: int,
    payload: WarehouseIn,
    user: ShipperDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> WarehouseOut:
    """货主修改自己仓库的主数据。"""
    try:
        return warehouse_service.update_warehouse(conn, user.id, warehouse_id, payload)
    except WarehouseNotFoundError:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="仓库不存在"
        )


@router.post("/{warehouse_id}/disable", response_model=WarehouseOut)
def disable_warehouse(
    warehouse_id: int,
    user: ShipperDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> WarehouseOut:
    """货主停用仓库，使其不再作为新订单的默认发货仓库。"""
    try:
        return warehouse_service.set_warehouse_status(
            conn, user.id, warehouse_id, "停用"
        )
    except WarehouseNotFoundError:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="仓库不存在"
        )


@router.post("/{warehouse_id}/enable", response_model=WarehouseOut)
def enable_warehouse(
    warehouse_id: int,
    user: ShipperDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> WarehouseOut:
    """货主重新启用仓库，恢复其作为新订单发货来源的资格。"""
    try:
        return warehouse_service.set_warehouse_status(
            conn, user.id, warehouse_id, "正常"
        )
    except WarehouseNotFoundError:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="仓库不存在"
        )
