"""仓库入参 / 出参模型。"""

from pydantic import BaseModel, ConfigDict, Field

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
PUBLIC = ConfigDict(extra="forbid")


class WarehouseIn(BaseModel):
    """新增 / 修改仓库请求。"""

    model_config = STRICT

    name: str = Field(min_length=1, max_length=128)
    contact: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=1, max_length=64)
    province: str = Field(min_length=1, max_length=64)
    city: str = Field(min_length=1, max_length=64)
    district: str = Field(min_length=1, max_length=64)
    detail_address: str = Field(min_length=1, max_length=256)
    type: str = Field(min_length=1, max_length=32)
    remarks: str = Field(default="", max_length=500)


class WarehouseOut(BaseModel):
    """仓库列表 / 详情出参。"""

    model_config = PUBLIC

    id: int
    shipper_id: int
    name: str
    location: str
    contact: str
    phone: str
    province: str
    city: str
    district: str
    detail_address: str
    type: str
    remarks: str
    status: str
    created_at: str
    updated_at: str
