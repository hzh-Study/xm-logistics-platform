"""领域异常：业务层失败语义，由路由转为 HTTP 响应。"""


class AuthenticationError(Exception):
    """手机号或口令不匹配。"""


class AccountUnavailableError(Exception):
    """账号状态不允许登录。"""


class PhoneAlreadyRegisteredError(Exception):
    """手机号已被注册。"""


class CarrierNotFoundError(Exception):
    """物流公司账号不存在。"""


class PhoneTakenError(Exception):
    """手机号已注册。"""


class CertificationStateError(Exception):
    """当前认证状态不允许该操作。"""


class CertificationNotFoundError(Exception):
    """认证提交记录不存在。"""


class NotPublishableError(Exception):
    """认证状态未达审核通过，不允许发布运输订单。"""


class WarehouseNotFoundError(Exception):
    """仓库不存在，或不属于当前货主。"""
