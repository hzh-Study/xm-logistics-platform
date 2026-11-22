"""在途异常上报与处理的入参 / 出参模型。"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
PUBLIC = ConfigDict(extra="forbid")

ISO_DT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"


def _is_relative_path(path: str) -> bool:
    """凭证路径只能是库内相对路径，拒绝绝对路径与目录穿越。"""
    parts = path.replace("\\", "/").split("/")
    return not (
        path.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:", path)
        or ".." in parts
    )


def _check_paths(paths: list[str]) -> None:
    """校验一组照片路径均为库内相对路径。"""
    for path in paths:
        if not _is_relative_path(path):
            raise ValueError("照片路径必须是库内相对路径")


class AnomalyIn(BaseModel):
    """司机提交在途异常：类型、说明、现场照片与发生时间。"""

    model_config = STRICT

    kind: Literal["故障", "事故", "封路", "拥堵", "货物异常", "预计延误", "其他"]
    detail: str = Field(min_length=1, max_length=500)
    photos: list[str] = Field(min_length=1, max_length=20)
    occurred_at: str = Field(pattern=ISO_DT)

    @model_validator(mode="after")
    def _paths_relative(self) -> "AnomalyIn":
        _check_paths(self.photos)
        return self


class AnomalyOut(BaseModel):
    """一条在途异常记录，只读追加。"""

    model_config = PUBLIC

    id: int
    anomaly_no: str
    task_id: int
    task_no: str
    order_id: int
    kind: str
    detail: str
    photos: list[str]
    occurred_at: str
    started: bool
    actor: str
    created_at: str


class HandlingIn(BaseModel):
    """物流公司追加异常处理记录；换车 / 换司机须带新旧与原因。"""

    model_config = STRICT

    result: Literal[
        "继续运输", "调整送达时间", "更换车辆", "更换司机", "重新安排运输", "终止运输"
    ]
    detail: str = Field(default="", max_length=500)
    new_vehicle_id: int | None = Field(default=None, gt=0)
    new_driver_account_id: int | None = Field(default=None, gt=0)
    adjusted_deliver_at: str | None = Field(default=None, pattern=ISO_DT)

    @model_validator(mode="after")
    def _required_fields(self) -> "HandlingIn":
        # 变更类结果必须给出新主体/新时间，终止运输必须写明原因
        if self.result == "更换车辆" and self.new_vehicle_id is None:
            raise ValueError("更换车辆须提供 new_vehicle_id")
        if self.result == "更换司机" and self.new_driver_account_id is None:
            raise ValueError("更换司机须提供 new_driver_account_id")
        if self.result == "调整送达时间" and not self.adjusted_deliver_at:
            raise ValueError("调整送达时间须提供 adjusted_deliver_at")
        if self.result == "终止运输" and not self.detail.strip():
            raise ValueError("终止运输须写明原因")
        return self


class HandlingOut(BaseModel):
    """一条异常处理记录：含 actor 角色、处理时间、最终结果与前后面。"""

    model_config = PUBLIC

    id: int
    handling_no: str
    anomaly_id: int
    task_id: int
    task_no: str
    result: str
    detail: str
    reason: str
    actor: str
    before_driver_account_id: int | None
    before_driver_name: str
    before_vehicle_id: int | None
    before_vehicle_plate: str
    after_driver_account_id: int | None
    after_driver_name: str
    after_vehicle_id: int | None
    after_vehicle_plate: str
    before_deliver_at: str | None
    after_deliver_at: str | None
    order_status: str
    task_status: str
    handled_at: str
    created_at: str


class ExceptionViewOut(BaseModel):
    """任务 / 订单的在途异常与处理记录只读视图。"""

    model_config = PUBLIC

    task_id: int
    task_no: str
    order_id: int
    order_no: str
    anomalies: list[AnomalyOut]
    handling_records: list[HandlingOut]
