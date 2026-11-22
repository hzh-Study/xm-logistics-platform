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


class DriverNotFoundError(Exception):
    """司机账号不属于当前物流公司，或不存在。"""


class DriverBindingOrderError(Exception):
    """首次登录必须先改密，再完成身份绑定。"""


class WarehouseNotFoundError(Exception):
    """仓库不存在，或不属于当前货主。"""


class OrderNotFoundError(Exception):
    """运输订单不存在，或不属于当前货主。"""


class PoolOrderNotFoundError(Exception):
    """货源不存在，或已不在公共订单池中。"""


class OrderNotAcceptableError(Exception):
    """运输订单当前不可承接（已被承接，先到先得）。"""

    def __init__(self) -> None:
        super().__init__("订单已被承接")


class VehicleNotFoundError(Exception):
    """车辆不存在，或不属于当前物流公司。"""


class VehicleNotAssignableError(Exception):
    """车辆状态不满足分配或派发新任务的条件。"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class VehicleOwnerDriverError(Exception):
    """个人车辆必须关联所属物流公司名下的司机。"""


class VehiclePlateTakenError(Exception):
    """车牌号已被登记。"""


class DispatchRuleError(Exception):
    """派单规则不满足；reason 为对外可见的具体原因。"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class TaskNotFoundError(Exception):
    """运输任务不存在，或不属于当前主体。"""


class TaskStateError(Exception):
    """运输任务当前状态不允许该操作。"""


class CheckinRuleError(Exception):
    """打卡 / 装货 / 起运前置条件不满足；reason 对外可见。"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class ExceptionRuleError(Exception):
    """异常处理前置条件不满足；reason 对外可见。"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason

