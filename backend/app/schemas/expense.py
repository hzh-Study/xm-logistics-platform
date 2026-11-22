"""报销费用提交、审核与支付的入参 / 出参模型。"""

import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
PUBLIC = ConfigDict(extra="forbid")

ISO_DT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
YUAN = r"^\d{1,10}(?:\.\d{1,2})?$"


def _is_relative_path(path: str) -> bool:
    """凭证路径只能是库内相对路径，拒绝绝对路径与目录穿越。"""
    parts = path.replace("\\", "/").split("/")
    return not (path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path) or ".." in parts)


def _check_paths(paths: list[str]) -> None:
    """校验一组凭证路径均为库内相对路径。"""
    for path in paths:
        if not _is_relative_path(path):
            raise ValueError("凭证路径必须是库内相对路径")


class ExpenseIn(BaseModel):
    """司机单笔提交报销费用：类型、金额、发生时间、说明与多张凭证。"""

    model_config = STRICT

    expense_type: Literal["油费", "过路费", "停车费", "维修费", "其他"]
    amount_yuan: str = Field(pattern=YUAN)
    incurred_at: str = Field(pattern=ISO_DT)
    description: str = Field(min_length=1, max_length=500)
    vouchers: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def _validate(self) -> "ExpenseIn":
        """金额须大于零，凭证路径须为库内相对路径。"""
        if Decimal(self.amount_yuan) <= 0:
            raise ValueError("报销费用金额须大于零")
        _check_paths(self.vouchers)
        return self


class ExpenseOut(BaseModel):
    """一笔报销费用：审核状态与支付状态独立，驳回原因对司机可见。"""

    model_config = PUBLIC

    id: int
    expense_no: str
    task_id: int
    task_no: str
    order_id: int
    driver_account_id: int
    driver_name: str
    carrier_account_id: int
    expense_type: str
    amount_yuan: str
    incurred_at: str
    description: str
    vouchers: list[str]
    review_status: str
    review_reason: str
    payment_status: str
    reviewed_at: str | None
    reviewed_by_account_id: int | None
    paid_at: str | None
    paid_by_account_id: int | None
    replaced_by: int | None
    superseded_by: int | None
    created_at: str


class ExpenseReviewIn(BaseModel):
    """物流公司审核：通过或驳回，驳回原因必填。"""

    model_config = STRICT

    decision: Literal["审核通过", "审核驳回"]
    reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _reason_required(self) -> "ExpenseReviewIn":
        """审核驳回时必须填写原因并让司机可见。"""
        if self.decision == "审核驳回" and not self.reason.strip():
            raise ValueError("驳回原因必填")
        return self
