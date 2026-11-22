"""发货地打卡、装货凭证与起运的入参 / 出参模型。"""

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
    """校验一组凭证路径均为库内相对路径。"""
    for path in paths:
        if not _is_relative_path(path):
            raise ValueError("照片路径必须是库内相对路径")


class CheckinIn(BaseModel):
    """司机提交发货地打卡：定位、到达时间、现场照片与备注。"""

    model_config = STRICT

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    arrived_at: str = Field(pattern=ISO_DT)
    photos: list[str] = Field(min_length=1, max_length=20)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _paths_relative(self) -> "CheckinIn":
        _check_paths(self.photos)
        return self


class CheckinOut(BaseModel):
    """一条发货地打卡记录；位置异常为告警而非驳回。"""

    model_config = PUBLIC

    id: int
    task_id: int
    task_no: str
    latitude: float
    longitude: float
    arrived_at: str
    photos: list[str]
    notes: str
    position_status: str
    distance_m: int | None
    warning: str
    exception_note_required: bool
    created_at: str


class ExceptionNoteIn(BaseModel):
    """司机对位置异常提交说明。"""

    model_config = STRICT

    note: str = Field(min_length=1, max_length=500)


class ExceptionNoteOut(BaseModel):
    """一条位置异常说明，只读追加。"""

    model_config = PUBLIC

    id: int
    checkin_id: int
    note: str
    created_at: str


class LoadingPhotosIn(BaseModel):
    """司机上传某一装货阶段的现场照片。"""

    model_config = STRICT

    phase: Literal["装货前", "装货中", "装货完成"]
    paths: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def _paths_relative(self) -> "LoadingPhotosIn":
        _check_paths(self.paths)
        return self


class LoadingPhotosOut(BaseModel):
    """一批装货阶段照片。"""

    model_config = PUBLIC

    id: int
    task_id: int
    phase: str
    paths: list[str]
    created_at: str


class LoadingAnomalyIn(BaseModel):
    """司机上报装货异常。"""

    model_config = STRICT

    kind: Literal["数量不符", "货损", "超载"]
    detail: str = Field(min_length=1, max_length=500)
    photos: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _paths_relative(self) -> "LoadingAnomalyIn":
        _check_paths(self.photos)
        return self


class LoadingAnomalyOut(BaseModel):
    """一条装货异常记录，只读追加。"""

    model_config = PUBLIC

    id: int
    task_id: int
    kind: str
    detail: str
    photos: list[str]
    created_at: str


class StartTransportIn(BaseModel):
    """起运前确认货物与车辆均已核对。"""

    model_config = STRICT

    cargo_confirmed: bool
    vehicle_confirmed: bool
    notes: str = Field(default="", max_length=500)


class DepartureConfirmationOut(BaseModel):
    """一条起运确认记录，只读追加。"""

    model_config = PUBLIC

    id: int
    task_id: int
    cargo_confirmed: bool
    vehicle_confirmed: bool
    notes: str
    created_at: str


class SiteCoordinateIn(BaseModel):
    """货主补录发货快照坐标，仅起运前可用。"""

    model_config = STRICT

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class SiteCoordinateOut(BaseModel):
    """补录后的发货快照坐标。"""

    model_config = PUBLIC

    order_id: int
    latitude: float
    longitude: float


class TaskProgressOut(BaseModel):
    """任务进度：司机 / 物流公司 / 货主共用，绝不含运费报价。"""

    model_config = PUBLIC

    task_id: int
    task_no: str
    order_id: int
    order_no: str
    status: str
    task_status: str
    order_status: str
    planned_load_at: str
    planned_deliver_at: str
    checkins: list[CheckinOut]
    exception_notes: list[ExceptionNoteOut]
    loading_photos: list[LoadingPhotosOut]
    loading_anomalies: list[LoadingAnomalyOut]
    confirmation: DepartureConfirmationOut | None
