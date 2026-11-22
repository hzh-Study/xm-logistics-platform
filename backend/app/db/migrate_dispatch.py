"""派单迁移（v9）：运输任务与派单历史；派单历史只读追加。"""

import sqlite3

_DISPATCH_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS transport_tasks (
        id                  INTEGER PRIMARY KEY,
        task_no             TEXT NOT NULL UNIQUE, -- 运输任务号，TASK-YYMMDD-0001
        order_id            INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT, -- 所属运输订单
        carrier_id          INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 承运物流公司
        driver_account_id   INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 执行司机账号
        vehicle_id          INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT, -- 执行车辆
        status              TEXT NOT NULL DEFAULT '待司机确认'
            CHECK(status IN ('待司机确认','待装货','运输中','待签收','待确认完成','已完成','异常','已拒绝')), -- 运输任务状态
        planned_load_at     TEXT NOT NULL, -- 计划装货时间，ISO 8601
        planned_deliver_at  TEXT NOT NULL, -- 计划送达时间，ISO 8601
        notes               TEXT NOT NULL DEFAULT '', -- 派单注意事项
        reject_reason       TEXT NOT NULL DEFAULT '', -- 司机拒绝原因
        accepted_at         TEXT, -- 司机确认时间，ISO 8601
        created_at          TEXT NOT NULL, -- 派单时间，ISO 8601
        CHECK(planned_deliver_at > planned_load_at)
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_tasks_carrier_status ON transport_tasks(carrier_id, status, id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_order ON transport_tasks(order_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_driver ON transport_tasks(driver_account_id, status, planned_load_at, planned_deliver_at)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_vehicle ON transport_tasks(vehicle_id, status, planned_load_at, planned_deliver_at)",
    """
    CREATE TABLE IF NOT EXISTS dispatch_history (
        id                        INTEGER PRIMARY KEY,
        dispatch_no               TEXT NOT NULL UNIQUE, -- 派单记录号，DISP-YYMMDD-0001
        order_id                  INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT, -- 运输订单
        task_id                   INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 运输任务
        action                    TEXT NOT NULL CHECK(action IN ('派单','重新派单','司机拒绝')), -- 派单动作
        original_driver_account_id INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 原司机
        original_vehicle_id       INTEGER REFERENCES vehicles(id) ON DELETE RESTRICT, -- 原车辆
        new_driver_account_id     INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 新司机
        new_vehicle_id            INTEGER REFERENCES vehicles(id) ON DELETE RESTRICT, -- 新车辆
        reason                    TEXT NOT NULL DEFAULT '', -- 变更 / 拒绝原因
        actor                     TEXT NOT NULL CHECK(actor IN ('物流公司','司机')), -- 记录发起角色
        replaced_by               INTEGER REFERENCES dispatch_history(id) ON DELETE RESTRICT, -- 更正记录
        created_at                TEXT NOT NULL -- 记录时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_dispatch_history_task ON dispatch_history(task_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_dispatch_history_order ON dispatch_history(order_id, id)",
    "CREATE TRIGGER IF NOT EXISTS trg_dispatch_history_no_update BEFORE UPDATE ON dispatch_history BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_dispatch_history_no_delete BEFORE DELETE ON dispatch_history BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
]


def migrate_dispatch(conn: sqlite3.Connection) -> None:
    """在已开启的事务内创建派单相关表与索引。"""
    for statement in _DISPATCH_SCHEMA:
        conn.execute(statement)
