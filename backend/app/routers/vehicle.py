"""车辆路由：公司侧车辆登记、状态管理与分配。"""

from typing import Literal

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

from app.dependencies import ActiveCarrierDep, CsrfDep, DbConnection
from app.exceptions import (
    DriverNotFoundError,
    VehicleNotAssignableError,
    VehicleNotFoundError,
    VehicleOwnerDriverError,
    VehiclePlateTakenError,
)
from app.schemas.vehicle import (
    Availability,
    DocumentStatus,
    Lifecycle,
    VehicleAssignIn,
    VehicleAvailabilityIn,
    VehicleCreateIn,
    VehicleDocumentStatusIn,
    VehicleLifecycleIn,
    VehicleOut,
)
from app.services import vehicle as vehicle_service

router = APIRouter(prefix="/api/carrier", tags=["carrier"])


@router.post("/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleCreateIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> VehicleOut:
    """物流公司登记公司车辆或司机个人车辆。"""
    try:
        return vehicle_service.create_vehicle(conn, user.id, payload)
    except VehiclePlateTakenError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="车牌号已被登记")
    except VehicleOwnerDriverError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(
    user: ActiveCarrierDep,
    conn: DbConnection,
    availability: Availability | None = None,
    lifecycle: Lifecycle | None = None,
    owner_type: Literal["公司", "司机"] | None = None,
    assignable: bool = False,
) -> list[VehicleOut]:
    """列出本公司车辆，可按两个独立状态与可分配性筛选。"""
    return vehicle_service.list_vehicles(
        conn, user.id, availability, lifecycle, owner_type, assignable
    )


@router.get("/vehicles/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: int, user: ActiveCarrierDep, conn: DbConnection) -> VehicleOut:
    """读取本公司名下车辆详情。"""
    try:
        return vehicle_service.get_vehicle(conn, user.id, vehicle_id)
    except VehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆不存在")


@router.post("/vehicles/{vehicle_id}/assign", response_model=VehicleOut)
def assign_vehicle(
    vehicle_id: int,
    payload: VehicleAssignIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> VehicleOut:
    """把公司名下车辆分配给本公司司机；状态不合格时拒绝并说明原因。"""
    try:
        return vehicle_service.assign_vehicle(
            conn, user.id, vehicle_id, payload.driver_account_id
        )
    except (VehicleNotFoundError, DriverNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆或司机不存在")
    except VehicleNotAssignableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason)


@router.post("/vehicles/{vehicle_id}/availability", response_model=VehicleOut)
def set_availability(
    vehicle_id: int,
    payload: VehicleAvailabilityIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> VehicleOut:
    """设置可用性；不影响生命周期。"""
    try:
        return vehicle_service.set_availability(
            conn, user.id, vehicle_id, payload.availability
        )
    except VehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆不存在")


@router.post("/vehicles/{vehicle_id}/lifecycle", response_model=VehicleOut)
def set_lifecycle(
    vehicle_id: int,
    payload: VehicleLifecycleIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> VehicleOut:
    """设置生命周期；不影响可用性。"""
    try:
        return vehicle_service.set_lifecycle(conn, user.id, vehicle_id, payload.lifecycle)
    except VehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆不存在")


@router.post("/vehicles/{vehicle_id}/document-status", response_model=VehicleOut)
def set_document_status(
    vehicle_id: int,
    payload: VehicleDocumentStatusIn,
    user: ActiveCarrierDep,
    conn: DbConnection,
    _csrf: CsrfDep,
) -> VehicleOut:
    """设置车辆证件状态。"""
    try:
        return vehicle_service.set_document_status(
            conn, user.id, vehicle_id, payload.document_status
        )
    except VehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆不存在")
