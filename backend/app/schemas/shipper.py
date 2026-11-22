"""货主认证入参 / 出参模型。"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
PUBLIC = ConfigDict(extra="forbid")


class ShipperRegisterIn(BaseModel):
    """货主注册请求。"""

    model_config = STRICT

    phone: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class CertificationIn(BaseModel):
    """认证资料提交请求。"""

    model_config = STRICT

    cert_type: Literal["个人", "企业"]
    name: str = Field(min_length=1, max_length=128)
    id_number: str = Field(min_length=1, max_length=64)
    contact_phone: str = Field(min_length=1, max_length=64)
    documents: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _paths_are_relative(self) -> "CertificationIn":
        # 凭证只存库内相对路径，拒绝绝对路径与目录穿越
        for path in self.documents:
            parts = path.replace("\\", "/").split("/")
            if (
                path.startswith(("/", "\\"))
                or re.match(r"^[A-Za-z]:", path)
                or ".." in parts
            ):
                raise ValueError("资料路径必须是库内相对路径")
        return self


class CertificationOut(BaseModel):
    """单条认证提交及其审核结果。"""

    model_config = PUBLIC

    id: int
    cert_type: str
    name: str
    id_number: str
    contact_phone: str
    documents: list[str]
    status: str
    rejection_reason: str | None
    reviewer_id: int | None
    reviewed_at: str | None
    submitted_at: str


class CertificationViewOut(BaseModel):
    """货主看到的认证状态、当前提交与全部提交历史。"""

    model_config = PUBLIC

    auth_status: str
    current: CertificationOut | None
    history: list[CertificationOut]


class ReviewIn(BaseModel):
    """管理员审核请求。"""

    model_config = STRICT

    decision: Literal["审核通过", "审核不通过"]
    rejection_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _reason_required_on_reject(self) -> "ReviewIn":
        if self.decision == "审核不通过" and not (self.rejection_reason or "").strip():
            raise ValueError("驳回原因必填")
        return self


class AdminCertOut(BaseModel):
    """管理员视角的一条货主认证记录。"""

    model_config = PUBLIC

    account_id: int
    phone: str
    auth_status: str
    account_status: str
    certification_id: int | None
    cert_type: str | None
    name: str | None
    id_number: str | None
    contact_phone: str | None
    documents: list[str]
    status: str | None
    rejection_reason: str | None
    submitted_at: str | None
    reviewed_at: str | None


class NotificationOut(BaseModel):
    """站内通知记录。"""

    model_config = PUBLIC

    id: int
    kind: str
    title: str
    body: str
    related_id: int | None
    created_at: str


class PublishIn(BaseModel):
    """发布运输订单的最小请求。"""

    model_config = STRICT

    cargo_name: str = Field(min_length=1, max_length=128)


class OrderOut(BaseModel):
    """运输订单最小出参。"""

    model_config = PUBLIC

    id: int
    order_no: str
    shipper_id: int
    cargo_name: str
    status: str
    created_at: str
