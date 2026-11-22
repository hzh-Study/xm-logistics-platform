"""订单取消与终止运输的入参 / 出参模型。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
PUBLIC = ConfigDict(extra="forbid")

OrderStatus = Literal[
    "待承接", "已承接", "运输中", "已完成", "取消处理中", "已取消", "异常处理中"
]


class CancelApplyIn(BaseModel):
    """货主申请取消：直接取消可不填原因，公司确认须写原因。"""

    model_config = STRICT

    reason: str | None = Field(default=None, max_length=500)


class CancelRejectIn(BaseModel):
    """物流公司驳回取消申请，原因必填。"""

    model_config = STRICT

    reason: str = Field(min_length=1, max_length=500)


class CancelOut(BaseModel):
    """一条取消申请当前态，读模型。"""

    model_config = PUBLIC

    id: int
    application_no: str
    order_id: int
    order_no: str
    shipper_id: int
    carrier_id: int | None
    mode: Literal["直接取消", "公司确认"]
    status: Literal["待公司处理", "已同意", "已驳回", "已直接取消"]
    reason: str
    handled_reason: str
    before_status: OrderStatus
    after_status: OrderStatus | None
    handled_by: int | None
    handled_at: str | None
    created_at: str


class CancelAuditOut(BaseModel):
    """一条追加不可变的取消操作留痕，读模型。"""

    model_config = PUBLIC

    id: int
    application_id: int
    event: Literal["申请", "直接取消", "同意", "驳回"]
    actor_id: int
    actor: Literal["货主", "物流公司"]
    from_status: OrderStatus
    to_status: OrderStatus
    reason: str
    detail: str
    created_at: str


class CancelViewOut(BaseModel):
    """取消申请当前态与全过程留痕。"""

    model_config = PUBLIC

    application: CancelOut | None
    audit: list[CancelAuditOut]


class CancelOptionsOut(BaseModel):
    """货主端取消入口是否可见及适用的取消方式。"""

    model_config = PUBLIC

    order_id: int
    status: OrderStatus
    can_cancel: bool
    mode: Literal["直接取消", "公司确认"] | None
    message: str
