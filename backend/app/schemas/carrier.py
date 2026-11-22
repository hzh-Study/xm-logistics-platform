"""物流公司认证入参 / 出参模型。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class CarrierRegisterIn(BaseModel):
    """物流公司注册请求。"""

    model_config = STRICT

    phone: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    company_name: str = Field(min_length=1, max_length=128)


class CertificationSubmitIn(BaseModel):
    """企业认证资料提交（提交 / 重新提交）。"""

    model_config = STRICT

    company_name: str = Field(min_length=1, max_length=128)
    license_no: str = Field(min_length=1, max_length=64)
    license_path: str = Field(min_length=1, max_length=512)
    legal_person: str = Field(min_length=1, max_length=64)
    contact_name: str = Field(min_length=1, max_length=64)
    contact_phone: str = Field(min_length=1, max_length=64)
    qualification_path: str = Field(min_length=1, max_length=512)
    note: str = Field(default="", max_length=1000)


class CertificationRecordOut(BaseModel):
    """一条认证记录（提交或审核），只读追加。"""

    model_config = ConfigDict(extra="forbid")

    id: int
    account_id: int
    kind: str
    decision: str
    company_name: str
    license_no: str
    license_path: str
    legal_person: str
    contact_name: str
    contact_phone: str
    qualification_path: str
    note: str
    reason: str
    actor: str
    replaced_by: int | None
    created_at: str


class CertificationViewOut(BaseModel):
    """当前认证状态、最新结果与全部历史记录。"""

    model_config = ConfigDict(extra="forbid")

    auth_status: str
    account_status: str
    latest: CertificationRecordOut | None
    records: list[CertificationRecordOut]


class CapabilitiesOut(BaseModel):
    """物流公司业务能力开关（认证状态与账号状态的投影）。"""

    model_config = ConfigDict(extra="forbid")

    can_accept_orders: bool
    can_dispatch: bool
    can_manage_drivers: bool
    can_manage_vehicles: bool
    reasons: list[str]


class BusinessAccessOut(BaseModel):
    """承运业务入口：放行时返回公司信息与可用能力。"""

    model_config = ConfigDict(extra="forbid")

    company_name: str
    auth_status: str
    capabilities: CapabilitiesOut


class ReviewIn(BaseModel):
    """管理员审核请求；驳回时 reason 必填。"""

    model_config = STRICT

    decision: Literal["通过", "驳回"]
    reason: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def reason_required_on_reject(self) -> "ReviewIn":
        """驳回必须携带原因。"""
        if self.decision == "驳回" and not self.reason:
            raise ValueError("驳回原因必填")
        return self


class AccountStatusIn(BaseModel):
    """管理员设置账号状态。"""

    model_config = STRICT

    account_status: Literal["正常使用", "已禁用"]


class CarrierSummaryOut(BaseModel):
    """管理员视角的物流公司摘要。"""

    model_config = ConfigDict(extra="forbid")

    account_id: int
    phone: str
    company_name: str
    license_no: str
    account_status: str
    auth_status: str
