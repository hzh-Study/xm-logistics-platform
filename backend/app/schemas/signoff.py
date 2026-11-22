"""收货地打卡、卸货凭证与签收完成的入参 / 出参模型。"""

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


class ArrivalCheckinIn(BaseModel):
    """司机提交收货地打卡：定位、到达时间、现场照片与备注。"""

    model_config = STRICT

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    arrived_at: str = Field(pattern=ISO_DT)
    photos: list[str] = Field(min_length=1, max_length=20)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _paths_relative(self) -> "ArrivalCheckinIn":
        _check_paths(self.photos)
        return self


class ArrivalCheckinOut(BaseModel):
    """一条收货地打卡记录；位置异常为告警而非驳回。"""

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


class ArrivalNoteIn(BaseModel):
    """司机对收货地位置异常提交说明。"""

    model_config = STRICT

    note: str = Field(min_length=1, max_length=500)


class ArrivalNoteOut(BaseModel):
    """一条收货地位置异常说明，只读追加。"""

    model_config = PUBLIC

    id: int
    checkin_id: int
    note: str
    created_at: str


class UnloadingPhotosIn(BaseModel):
    """司机上传某一卸货阶段的现场照片。"""

    model_config = STRICT

    phase: Literal["卸货前", "卸货中", "卸货完成"]
    paths: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def _paths_relative(self) -> "UnloadingPhotosIn":
        _check_paths(self.paths)
        return self


class UnloadingPhotosOut(BaseModel):
    """一批卸货阶段照片。"""

    model_config = PUBLIC

    id: int
    task_id: int
    phase: str
    paths: list[str]
    created_at: str


class UnloadingAnomalyIn(BaseModel):
    """司机上报卸货异常。"""

    model_config = STRICT

    kind: Literal["货损", "数量不符", "拒收"]
    detail: str = Field(min_length=1, max_length=500)
    photos: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _paths_relative(self) -> "UnloadingAnomalyIn":
        _check_paths(self.photos)
        return self


class UnloadingAnomalyOut(BaseModel):
    """一条卸货异常记录，只读追加。"""

    model_config = PUBLIC

    id: int
    task_id: int
    kind: str
    detail: str
    photos: list[str]
    created_at: str


class SignoffIn(BaseModel):
    """司机提交签收资料：收货情况、时间、收货人、签收照片、凭证与备注。"""

    model_config = STRICT

    receiving_condition: Literal["完好", "货损", "数量不符", "其他"]
    received_at: str = Field(pattern=ISO_DT)
    receiver_name: str = Field(min_length=1, max_length=100)
    signature_photos: list[str] = Field(min_length=1, max_length=20)
    vouchers: list[str] = Field(min_length=1, max_length=20)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _paths_relative(self) -> "SignoffIn":
        _check_paths(self.signature_photos)
        _check_paths(self.vouchers)
        return self


class SignoffVoucherOut(BaseModel):
    """一份签收凭证：公司据以确认任务完成，货主只读。"""

    model_config = PUBLIC

    id: int
    voucher_no: str
    task_id: int
    task_no: str
    order_id: int
    receiving_condition: str
    received_at: str
    receiver_name: str
    signature_photos: list[str]
    vouchers: list[str]
    notes: str
    created_at: str


class SignoffConfirmIn(BaseModel):
    """物流公司依据签收凭证确认完成。"""

    model_config = STRICT

    confirmed: bool
    notes: str = Field(default="", max_length=500)


class SignoffConfirmationOut(BaseModel):
    """一条公司确认记录，只读追加。"""

    model_config = PUBLIC

    id: int
    task_id: int
    voucher_id: int
    carrier_account_id: int
    notes: str
    created_at: str


class ReceivingCoordinateIn(BaseModel):
    """货主补录收货快照坐标，仅运输前可用。"""

    model_config = STRICT

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ReceivingCoordinateOut(BaseModel):
    """补录后的收货快照坐标。"""

    model_config = PUBLIC

    order_id: int
    latitude: float
    longitude: float
