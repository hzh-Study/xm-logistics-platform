"""车辆登记、状态管理与分配的入参 / 出参模型。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

VehicleType = Literal["厢式货车", "平板货车", "高栏货车", "冷藏车", "其他"]
OwnerType = Literal["公司", "司机"]
Availability = Literal["可用", "占用中", "暂停使用"]
Lifecycle = Literal["在册", "维修中", "已停用"]
DocumentStatus = Literal["待审核", "有效", "已过期"]


class VehicleCreateIn(BaseModel):
    """物流公司登记公司车辆或司机个人车辆。"""

    model_config = STRICT

    plate_no: str = Field(min_length=1, max_length=32)
    vehicle_type: VehicleType
    length_m: float = Field(gt=0, le=30)
    max_load_kg: int = Field(gt=0, le=100000)
    owner_type: OwnerType
    owner_driver_id: int | None = None
    document_status: DocumentStatus = "待审核"


class VehicleAssignIn(BaseModel):
    """把公司名下车辆分配给本公司司机。"""

    model_config = STRICT

    driver_account_id: int = Field(gt=0)


class VehicleAvailabilityIn(BaseModel):
    """设置车辆可用性，不影响生命周期。"""

    model_config = STRICT

    availability: Availability


class VehicleLifecycleIn(BaseModel):
    """设置车辆生命周期，不影响可用性。"""

    model_config = STRICT

    lifecycle: Lifecycle


class VehicleDocumentStatusIn(BaseModel):
    """设置车辆证件状态。"""

    model_config = STRICT

    document_status: DocumentStatus


class VehicleOut(BaseModel):
    """物流公司视角的车辆资料与两个独立状态维度。"""

    model_config = ConfigDict(extra="forbid")

    id: int
    plate_no: str
    vehicle_type: str
    length_m: float
    max_load_kg: int
    owner_type: str
    actual_owner: str
    owner_driver_id: int | None
    current_driver_id: int | None
    current_driver: str
    availability: str
    lifecycle: str
    document_status: str
    assignable: bool
    created_at: str
