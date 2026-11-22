"""平台异常管理与车辆转籍迁移（v16）：异常处理记录与转籍历史追加不可变。

平台异常登记、处理结果、车辆转籍前后归属均只 INSERT；任何更正写新记录，
不覆盖原始业务记录。转籍不改写历史任务中的车辆引用。
"""

import sqlite3

_PLATFORM_EXCEPTION_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS platform_exceptions (
        id                 INTEGER PRIMARY KEY,
        exception_no       TEXT NOT NULL UNIQUE, -- 平台异常记录号，PFEXC-YYMMDD-0001
        category           TEXT NOT NULL
            CHECK(category IN ('投诉','订单纠纷','公司违规','司机违规','车辆异常','任务长期未完成','费用纠纷')), -- 平台异常类别
        subject            TEXT NOT NULL, -- 被反映对象描述
        detail             TEXT NOT NULL, -- 异常说明
        subject_account_id INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 涉及主体账号
        order_id           INTEGER REFERENCES orders(id) ON DELETE RESTRICT, -- 关联运输订单
        task_id            INTEGER REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 关联运输任务
        vehicle_id         INTEGER REFERENCES vehicles(id) ON DELETE RESTRICT, -- 关联车辆
        actor_id           INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 登记管理员
        actor              TEXT NOT NULL DEFAULT '管理员' CHECK(actor IN ('管理员')), -- 登记角色
        replaced_by        INTEGER REFERENCES platform_exceptions(id) ON DELETE RESTRICT, -- 更正记录
        created_at         TEXT NOT NULL -- 登记时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_exception_handling (
        id           INTEGER PRIMARY KEY,
        handling_no  TEXT NOT NULL UNIQUE, -- 平台异常处理记录号，PFH-YYMMDD-0001
        exception_id INTEGER NOT NULL REFERENCES platform_exceptions(id) ON DELETE RESTRICT, -- 所属平台异常
        result       TEXT NOT NULL
            CHECK(result IN ('已处理','已调解','已处罚','已驳回','已归档')), -- 处理结果
        reason       TEXT NOT NULL, -- 处理原因
        detail       TEXT NOT NULL DEFAULT '', -- 处理说明
        actor_id     INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 处理管理员
        actor        TEXT NOT NULL DEFAULT '管理员' CHECK(actor IN ('管理员')), -- 处理角色
        order_status TEXT, -- 处理后订单状态投影，可为已取消等，无 CHECK
        task_status  TEXT, -- 处理后任务状态投影，可含已取消，无 CHECK
        handled_at   TEXT NOT NULL, -- 处理时间，ISO 8601
        replaced_by  INTEGER REFERENCES platform_exception_handling(id) ON DELETE RESTRICT, -- 更正记录
        created_at   TEXT NOT NULL -- 记录时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS vehicle_transfers (
        id                INTEGER PRIMARY KEY,
        transfer_no       TEXT NOT NULL UNIQUE, -- 转籍记录号，TR-YYMMDD-0001
        vehicle_id        INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT, -- 转籍车辆
        plate_no          TEXT NOT NULL, -- 车牌号快照
        before_carrier_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 转出物流公司
        after_carrier_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 转入物流公司
        reason            TEXT NOT NULL, -- 转籍原因
        actor_id          INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 处理管理员
        actor             TEXT NOT NULL DEFAULT '管理员' CHECK(actor IN ('管理员')), -- 处理角色
        replaced_by       INTEGER REFERENCES vehicle_transfers(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL -- 转籍时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_platform_exceptions_category ON platform_exceptions(category, id)",
    "CREATE INDEX IF NOT EXISTS idx_platform_handling_exception ON platform_exception_handling(exception_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_vehicle_transfers_vehicle ON vehicle_transfers(vehicle_id, id)",
    "CREATE TRIGGER IF NOT EXISTS trg_platform_exceptions_no_update BEFORE UPDATE ON platform_exceptions BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_platform_exceptions_no_delete BEFORE DELETE ON platform_exceptions BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_platform_handling_no_update BEFORE UPDATE ON platform_exception_handling BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_platform_handling_no_delete BEFORE DELETE ON platform_exception_handling BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_vehicle_transfers_no_update BEFORE UPDATE ON vehicle_transfers BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_vehicle_transfers_no_delete BEFORE DELETE ON vehicle_transfers BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
]


def migrate_platform_exception(conn: sqlite3.Connection) -> None:
    """在已开启的事务内幂等创建平台异常与转籍历史表、索引和不可变触发器。"""
    for statement in _PLATFORM_EXCEPTION_SCHEMA:
        conn.execute(statement)
