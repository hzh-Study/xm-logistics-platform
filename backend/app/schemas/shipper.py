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


def _is_relative_path(path: str) -> bool:
    """凭证路径只能是库内相对路径，拒绝绝对路径与目录穿越。"""
    parts = path.replace("\\", "/").split("/")
    return not (
        path.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:", path)
        or ".." in parts
    )


class PublishIn(BaseModel):
    """发布运输订单请求；未填字段沿用默认值以兼容早期最小发布。"""

    model_config = STRICT

    cargo_name: str = Field(min_length=1, max_length=128)
    cargo_type: str = Field(default="", max_length=64)
    quantity: str = Field(default="", max_length=64)
    weight: str = Field(default="", max_length=64)
    volume: str = Field(default="", max_length=64)
    packaging: str = Field(default="", max_length=64)
    cargo_photos: list[str] = Field(default_factory=list, max_length=20)
    cargo_remarks: str = Field(default="", max_length=500)

    shipping_source: Literal["仓库", "临时地址"] | None = None
    warehouse_id: int | None = Field(default=None, ge=1)
    shipping_name: str = Field(default="", max_length=128)
    shipping_contact: str = Field(default="", max_length=64)
    shipping_phone: str = Field(default="", max_length=64)
    shipping_province: str = Field(default="", max_length=64)
    shipping_city: str = Field(default="", max_length=64)
    shipping_district: str = Field(default="", max_length=64)
    shipping_detail_address: str = Field(default="", max_length=256)

    receiving_name: str = Field(default="", max_length=128)
    receiving_contact: str = Field(default="", max_length=64)
    receiving_phone: str = Field(default="", max_length=64)
    receiving_province: str = Field(default="", max_length=64)
    receiving_city: str = Field(default="", max_length=64)
    receiving_district: str = Field(default="", max_length=64)
    receiving_detail_address: str = Field(default="", max_length=256)

    vehicle_type: str = Field(default="", max_length=64)
    vehicle_length: str = Field(default="", max_length=64)
    load_requirement: str = Field(default="", max_length=64)
    cold_chain: bool = False
    rain_protection: bool = False
    enclosed_body: bool = False
    special_loading: bool = False
    other_services: str = Field(default="", max_length=500)
    transport_remarks: str = Field(default="", max_length=500)

    quote_method: Literal["固定", "可协商", "其他"] = "可协商"
    quote_amount_yuan: str | None = Field(
        default=None, pattern=r"^\d{1,9}(\.\d{1,2})?$"
    )
    accept_bargain: bool = False
    quote_remarks: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _check_publish(self) -> "PublishIn":
        # 照片只存库内相对路径
        for path in self.cargo_photos:
            if not _is_relative_path(path):
                raise ValueError("货物照片必须是库内相对路径")
        # 仓库发货必须指定仓库，且不能同时给出临时地址字段
        temp = (
            self.shipping_name,
            self.shipping_contact,
            self.shipping_phone,
            self.shipping_province,
            self.shipping_city,
            self.shipping_district,
            self.shipping_detail_address,
        )
        if self.warehouse_id is not None:
            if self.shipping_source == "临时地址" or any(temp):
                raise ValueError("选择仓库发货时不能填写临时地址")
        elif self.shipping_source == "仓库":
            raise ValueError("选择仓库发货时必须指定仓库")
        elif self.shipping_source == "临时地址" or any(temp):
            if not all(temp):
                raise ValueError("临时地址发货需填写名称、联系人、电话与完整地址")
        recv = (
            self.receiving_name,
            self.receiving_contact,
            self.receiving_phone,
            self.receiving_province,
            self.receiving_city,
            self.receiving_district,
            self.receiving_detail_address,
        )
        if any(recv) and not all(recv):
            raise ValueError("收货信息需填写名称、联系人、电话与完整地址")
        if self.quote_method == "固定" and not self.quote_amount_yuan:
            raise ValueError("固定报价必须填写金额")
        return self


class ShippingSnapshotOut(BaseModel):
    """订单上固化的发货快照，不随仓库变化而改写。"""

    model_config = PUBLIC

    source: str
    warehouse_id: int | None
    name: str
    contact: str
    phone: str
    province: str
    city: str
    district: str
    detail_address: str
    type: str


class ReceivingSnapshotOut(BaseModel):
    """订单上固化的收货快照。"""

    model_config = PUBLIC

    name: str
    contact: str
    phone: str
    province: str
    city: str
    district: str
    detail_address: str


class OrderOut(BaseModel):
    """运输订单出参：货运双方可见，运费报价对司机不可见。"""

    model_config = PUBLIC

    id: int
    order_no: str
    shipper_id: int
    cargo_name: str
    status: str
    carrier_id: int | None  # 承接物流公司账号 id，待承接时为空
    accepted_at: str | None  # 承接时间，ISO 8601
    created_at: str
    cargo_type: str
    quantity: str
    weight: str
    volume: str
    packaging: str
    cargo_photos: list[str]
    cargo_remarks: str
    shipping_snapshot: ShippingSnapshotOut
    receiving_snapshot: ReceivingSnapshotOut
    vehicle_type: str
    vehicle_length: str
    load_requirement: str
    cold_chain: bool
    rain_protection: bool
    enclosed_body: bool
    special_loading: bool
    other_services: str
    transport_remarks: str
    quote_method: str
    quote_amount_yuan: str
    accept_bargain: bool
    quote_remarks: str
