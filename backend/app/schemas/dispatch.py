"""派单、运输任务与司机确认的入参 / 出参模型。"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
PUBLIC = ConfigDict(extra="forbid")

ISO_DT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"


def _parse_dt(value: str) -> datetime:
    """把 ISO 8601 字符串解析为带时区的 datetime，供区间比较。"""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class DispatchCreateIn(BaseModel):
    """物流公司为已承接订单创建运输任务。"""

    model_config = STRICT

    order_id: int = Field(gt=0)
    driver_account_id: int = Field(gt=0)
    vehicle_id: int = Field(gt=0)
    planned_load_at: str = Field(pattern=ISO_DT)
    planned_deliver_at: str = Field(pattern=ISO_DT)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _window_valid(self) -> "DispatchCreateIn":
        # 计划送达须晚于计划装货，避免生成非法时间区间
        if _parse_dt(self.planned_deliver_at) <= _parse_dt(self.planned_load_at):
            raise ValueError("计划送达时间须晚于计划装货时间")
        return self


class RedispatchIn(BaseModel):
    """未起运重新派单：更换执行司机 / 车辆并说明原因。"""

    model_config = STRICT

    driver_account_id: int = Field(gt=0)
    vehicle_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=500)


class DriverRejectIn(BaseModel):
    """司机拒绝任务，原因必填。"""

    model_config = STRICT

    reason: str = Field(min_length=1, max_length=500)


class TaskOut(BaseModel):
    """物流公司视角的运输任务。"""

    model_config = PUBLIC

    id: int
    task_no: str
    order_id: int
    order_no: str
    carrier_id: int
    driver_account_id: int
    driver_name: str
    driver_phone: str
    vehicle_id: int
    vehicle_plate: str
    status: str
    planned_load_at: str
    planned_deliver_at: str
    notes: str
    reject_reason: str
    accepted_at: str | None
    created_at: str


class DispatchHistoryOut(BaseModel):
    """一条派单 / 重新派单 / 拒绝留痕，只读追加。"""

    model_config = PUBLIC

    id: int
    dispatch_no: str
    order_id: int
    task_id: int
    action: str
    original_driver_account_id: int | None
    original_driver_name: str
    original_vehicle_id: int | None
    original_vehicle_plate: str
    new_driver_account_id: int | None
    new_driver_name: str
    new_vehicle_id: int | None
    new_vehicle_plate: str
    reason: str
    actor: str
    replaced_by: int | None
    created_at: str


class DriverPlaceOut(BaseModel):
    """司机可见的发货 / 收货地点快照，仅含执行所需字段。"""

    model_config = PUBLIC

    name: str
    contact: str
    phone: str
    province: str
    city: str
    district: str
    detail_address: str


class DriverTaskOut(BaseModel):
    """司机 H5 任务详情：不含任何运费报价字段。"""

    model_config = PUBLIC

    task_id: int
    task_no: str
    order_id: int
    order_no: str
    status: str
    planned_load_at: str
    planned_deliver_at: str
    notes: str
    cargo_name: str
    cargo_type: str
    quantity: str
    weight: str
    volume: str
    packaging: str
    cargo_photos: list[str]
    cargo_remarks: str
    shipping: DriverPlaceOut
    receiving: DriverPlaceOut
    vehicle_type: str
    vehicle_length: str
    load_requirement: str
    cold_chain: bool
    rain_protection: bool
    enclosed_body: bool
    special_loading: bool
    other_services: str
    transport_remarks: str
    vehicle_plate: str
    vehicle_type_actual: str
    vehicle_length_m: float
    vehicle_max_load_kg: int
    carrier_company: str
    accepted_at: str | None
    reject_reason: str
    created_at: str
