"""司机创建、身份绑定与三类状态的入参 / 出参模型。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

Availability = Literal["可派单", "任务占用中", "暂停接单"]
Employment = Literal["在职", "离职"]
DriverAccountStatus = Literal["正常使用", "已禁用"]


class DriverCreateIn(BaseModel):
    """物流公司创建司机账号（手机号 + 临时密码）。"""

    model_config = STRICT

    phone: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    id_number: str = Field(default="", max_length=64)
    license_no: str = Field(default="", max_length=64)
    license_type: str = Field(default="", max_length=32)
    license_expiry: str = Field(default="", max_length=32)


class DriverUpdateIn(BaseModel):
    """修改司机基本资料；身份 / 资格字段变更触发重新审核。"""

    model_config = STRICT

    name: str = Field(min_length=1, max_length=64)
    id_number: str | None = Field(default=None, max_length=64)
    license_no: str | None = Field(default=None, max_length=64)
    license_type: str | None = Field(default=None, max_length=32)
    license_expiry: str | None = Field(default=None, max_length=32)


class AvailabilityIn(BaseModel):
    """设置司机接单可用性。"""

    model_config = STRICT

    availability: Availability


class EmploymentIn(BaseModel):
    """设置司机雇佣关系。"""

    model_config = STRICT

    employment: Employment


class DriverAccountStatusIn(BaseModel):
    """物流公司设置旗下司机账号状态。"""

    model_config = STRICT

    account_status: DriverAccountStatus


class ChangePasswordIn(BaseModel):
    """司机首次登录强制修改口令。"""

    model_config = STRICT

    new_password: str = Field(min_length=8, max_length=128)


class DriverBindingIn(BaseModel):
    """司机补全身份与驾驶资格资料，完成身份绑定。"""

    model_config = STRICT

    name: str = Field(min_length=1, max_length=64)
    id_number: str = Field(min_length=1, max_length=64)
    license_no: str = Field(min_length=1, max_length=64)
    license_type: str = Field(min_length=1, max_length=32)
    license_expiry: str = Field(min_length=1, max_length=32)


class DriverOut(BaseModel):
    """物流公司视角的司机完整资料与三类独立状态。"""

    model_config = ConfigDict(extra="forbid")

    account_id: int
    phone: str
    name: str
    auth_status: str
    account_status: str
    id_number: str
    license_no: str
    license_type: str
    license_expiry: str
    qualification: str
    availability: str
    employment: str
    departure_date: str | None
    binding_complete: bool
    must_change_password: bool
    current_vehicle: str
    current_task: str
    historical_task_count: int
    can_dispatch_new: bool
    can_continue_in_flight: bool


class DriverIdentityRecord(BaseModel):
    """一条身份 / 驾驶资格提交历史，只读追加。"""

    model_config = ConfigDict(extra="forbid")

    id: int
    account_id: int
    name: str
    id_number: str
    license_no: str
    license_type: str
    license_expiry: str
    reason: str
    actor: str
    replaced_by: int | None
    created_at: str


class OnboardingOut(BaseModel):
    """司机首次登录强制流程的当前状态。"""

    model_config = ConfigDict(extra="forbid")

    must_change_password: bool
    binding_complete: bool
    company_name: str
    auth_status: str
    blocked_reason: str


class DriverSelfOut(BaseModel):
    """司机本人可见的自身资料。"""

    model_config = ConfigDict(extra="forbid")

    account_id: int
    phone: str
    name: str
    company_name: str
    auth_status: str
    account_status: str
    availability: str
    employment: str
    binding_complete: bool
    must_change_password: bool
