"""管理员平台入参 / 出参模型：统计、全平台查询、统一审核、账号状态与公告。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
PUBLIC = ConfigDict(extra="forbid")


class AdminStatsOut(BaseModel):
    """管理员首页运营统计。"""

    model_config = PUBLIC

    shipper_count: int
    carrier_count: int
    driver_count: int
    vehicle_count: int
    orders_pending_accept: int  # 待承接
    orders_in_transit: int  # 运输中
    orders_completed: int  # 已完成
    orders_exception: int  # 异常处理中
    pending_certifications: int  # 待审核认证账号数


class ShipperSummaryOut(BaseModel):
    """管理员视角的货主摘要。"""

    model_config = PUBLIC

    account_id: int
    phone: str
    company_name: str
    profile_type: str
    account_status: str
    auth_status: str


class DriverSummaryOut(BaseModel):
    """管理员视角的司机摘要。"""

    model_config = PUBLIC

    account_id: int
    phone: str
    driver_name: str
    license_no: str
    carrier_id: int | None
    account_status: str
    auth_status: str
    availability: str
    employment: str


class VehicleSummaryOut(BaseModel):
    """管理员视角的车辆摘要。"""

    model_config = PUBLIC

    id: int
    plate_no: str
    carrier_id: int
    vehicle_type: str
    availability: str
    lifecycle: str
    document_status: str
    document_review_status: str


class CertItemOut(BaseModel):
    """统一认证列表中的一条待处理/已处理认证。"""

    model_config = PUBLIC

    id: int  # 目标记录 id（认证提交 / 账号 / 车辆）
    category: str  # 货主/企业/司机/驾驶资格/车辆证件
    subject_id: int  # 所属主体账号 id（车辆证件为车辆 id）
    subject_name: str
    auth_status: str  # 当前状态（认证/资格/证件审核）
    account_status: str  # 账号状态（车辆证件为空）
    submitted_at: str | None
    reason: str | None  # 最近一次驳回原因
    detail: str


class UnifiedReviewIn(BaseModel):
    """统一认证审核请求；驳回时 reason 必填。"""

    model_config = STRICT

    category: Literal["货主", "企业", "司机", "驾驶资格", "车辆证件"]
    target_id: int = Field(ge=1)
    decision: Literal["审核通过", "审核不通过"]
    reason: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def reason_required_on_reject(self) -> "UnifiedReviewIn":
        """驳回必须携带原因。"""
        if self.decision == "审核不通过" and not (self.reason or "").strip():
            raise ValueError("驳回原因必填")
        return self


class CertReviewOut(BaseModel):
    """一次统一审核的结果留痕。"""

    model_config = PUBLIC

    category: str
    target_id: int
    decision: str
    reason: str
    actor_id: int
    created_at: str


class AccountStatusIn(BaseModel):
    """管理员统一设置账号状态。"""

    model_config = STRICT

    account_status: Literal["正常使用", "已禁用"]


class AccountStatusOut(BaseModel):
    """账号状态处置结果。"""

    model_config = PUBLIC

    account_id: int
    role: str
    account_status: str


class AnnouncementIn(BaseModel):
    """发布平台公告。"""

    model_config = STRICT

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    scope: Literal["全部", "货主", "物流公司", "司机"] = "全部"


class AnnouncementOut(BaseModel):
    """平台公告出参：channel 表明独立于业务通知通道。"""

    model_config = PUBLIC

    id: int
    title: str
    body: str
    scope: str
    publisher_id: int
    published_at: str
    channel: str


class NoticeIn(BaseModel):
    """发布平台通知。"""

    model_config = STRICT

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    scope: Literal["全部", "货主", "物流公司", "司机"] = "全部"


class NoticeOut(BaseModel):
    """平台通知出参：channel 表明独立于业务通知通道。"""

    model_config = PUBLIC

    id: int
    title: str
    body: str
    scope: str
    publisher_id: int
    published_at: str
    channel: str
