"""领域异常：业务层失败语义，由路由转为 HTTP 响应。"""


class AuthenticationError(Exception):
    """手机号或口令不匹配。"""


class AccountUnavailableError(Exception):
    """账号状态不允许登录。"""
