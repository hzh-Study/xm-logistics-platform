"""鉴权入参 / 出参模型。"""

from pydantic import BaseModel, ConfigDict, Field

STRICT = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class LoginIn(BaseModel):
    """登录请求。"""

    model_config = STRICT

    phone: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """当前用户公开信息。"""

    model_config = ConfigDict(extra="forbid")

    id: int
    phone: str
    role: str
    account_status: str
    auth_status: str


class MeOut(UserOut):
    """当前用户与会话 CSRF，供页面刷新后恢复登录态。"""

    csrf_token: str


class LoginOut(BaseModel):
    """登录响应：用户信息与 CSRF token。"""

    model_config = ConfigDict(extra="forbid")

    user: UserOut
    csrf_token: str
