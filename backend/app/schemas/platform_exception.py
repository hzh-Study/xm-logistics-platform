"""平台异常管理与车辆转籍的入参 / 出参模型。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
PUBLIC = ConfigDict(extra="forbid")

PlatformExceptionCategory = Literal[
    "投诉", "订单纠纷", "公司违规", "司机违规", "车辆异常", "任务长期未完成", "费用纠纷"
]
PlatformResult = Literal["已处理", "已调解", "已处罚", "已驳回", "已归档"]


class PlatformExceptionIn(BaseModel):
    """管理员登记平台异常：类别、对象描述、说明与可选关联业务记录。"""

    model_config = STRICT

    category: PlatformExceptionCategory
    subject: str = Field(min_length=1, max_length=200)
    detail: str = Field(min_length=1, max_length=2000)
    subject_account_id: int | None = Field(default=None, gt=0)
    order_id: int | None = Field(default=None, gt=0)
    task_id: int | None = Field(default=None, gt=0)
    vehicle_id: int | None = Field(default=None, gt=0)


class PlatformExceptionOut(BaseModel):
    """一条平台异常登记记录，只读追加。"""

    model_config = PUBLIC

    id: int
    exception_no: str
    category: str
    subject: str
    detail: str
    subject_account_id: int | None
    order_id: int | None
    task_id: int | None
    vehicle_id: int | None
    actor: str
    created_at: str


class PlatformHandlingIn(BaseModel):
    """管理员追加平台异常处理记录：结果与原因必填。"""

    model_config = STRICT

    result: PlatformResult
    reason: str = Field(min_length=1, max_length=1000)
    detail: str = Field(default="", max_length=2000)


class PlatformHandlingOut(BaseModel):
    """一条平台异常处理记录：actor 角色、原因、结果、时间与状态投影。"""

    model_config = PUBLIC

    id: int
    handling_no: str
    exception_id: int
    result: str
    reason: str
    detail: str
    actor: str
    actor_id: int
    order_status: str | None
    task_status: str | None
    handled_at: str
    created_at: str


class PlatformExceptionViewOut(BaseModel):
    """平台异常登记与全部追加处理记录的只读视图。"""

    model_config = PUBLIC

    exception: PlatformExceptionOut
    handling_records: list[PlatformHandlingOut]


class VehicleTransferIn(BaseModel):
    """车辆转籍：车辆、转入物流公司账号与转籍原因。"""

    model_config = STRICT

    vehicle_id: int = Field(gt=0)
    to_carrier_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=1000)


class VehicleTransferOut(BaseModel):
    """一条车辆转籍历史：转出 / 转入归属快照与处理角色、时间。"""

    model_config = PUBLIC

    id: int
    transfer_no: str
    vehicle_id: int
    plate_no: str
    before_carrier_id: int
    after_carrier_id: int
    reason: str
    actor: str
    actor_id: int
    created_at: str
