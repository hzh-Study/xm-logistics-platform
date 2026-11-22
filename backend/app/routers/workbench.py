"""工作台入口路由：按角色门禁隔离，骨架阶段返回最小信息。"""

from fastapi import APIRouter

from app.dependencies import AdminDep, CarrierDep, DriverDep, ShipperDep
from app.schemas.auth import UserOut

router = APIRouter(prefix="/api", tags=["workbench"])


@router.get("/driver/workbench", response_model=UserOut)
def driver_workbench(user: DriverDep) -> UserOut:
    """司机工作台入口。"""
    return user


@router.get("/shipper/workbench", response_model=UserOut)
def shipper_workbench(user: ShipperDep) -> UserOut:
    """货主工作台入口。"""
    return user


@router.get("/carrier/workbench", response_model=UserOut)
def carrier_workbench(user: CarrierDep) -> UserOut:
    """物流公司工作台入口。"""
    return user


@router.get("/admin/workbench", response_model=UserOut)
def admin_workbench(user: AdminDep) -> UserOut:
    """管理员工作台入口。"""
    return user
