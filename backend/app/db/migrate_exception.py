"""在途异常与换车换司机迁移（v11）：异常上报、处理记录与前后留痕。

异常与处理记录一律追加不可变；换车换司机只记前后与原因，不覆盖打卡与照片。
"""

import sqlite3

_EXCEPTION_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS transport_anomalies (
        id                INTEGER PRIMARY KEY,
        anomaly_no        TEXT NOT NULL UNIQUE, -- 在途异常记录号，EXC-YYMMDD-0001
        task_id           INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        order_id          INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT, -- 所属运输订单
        driver_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 上报司机
        kind              TEXT NOT NULL CHECK(kind IN ('故障','事故','封路','拥堵','货物异常','预计延误','其他')), -- 异常类型
        detail            TEXT NOT NULL, -- 异常说明
        photos            TEXT NOT NULL DEFAULT '[]', -- 现场照片相对路径 JSON 数组
        occurred_at       TEXT NOT NULL, -- 异常发生时间，ISO 8601
        started           INTEGER NOT NULL CHECK(started IN (0,1)), -- 上报时是否已起运：0/1
        actor             TEXT NOT NULL DEFAULT '司机' CHECK(actor IN ('司机','物流公司','管理员')), -- 记录发起角色
        reason            TEXT NOT NULL DEFAULT '', -- 记录原因
        replaced_by       INTEGER REFERENCES transport_anomalies(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL -- 记录时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS exception_handling_records (
        id                       INTEGER PRIMARY KEY,
        handling_no              TEXT NOT NULL UNIQUE, -- 异常处理记录号，EXCH-YYMMDD-0001
        anomaly_id               INTEGER NOT NULL REFERENCES transport_anomalies(id) ON DELETE RESTRICT, -- 关联异常
        task_id                  INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        order_id                 INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT, -- 所属运输订单
        result                   TEXT NOT NULL CHECK(result IN ('继续运输','调整送达时间','更换车辆','更换司机','重新安排运输','终止运输')), -- 处理结果
        detail                   TEXT NOT NULL DEFAULT '', -- 处理说明
        actor_id                 INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 处理人账号
        actor                    TEXT NOT NULL CHECK(actor IN ('物流公司','司机','管理员')), -- 处理人角色
        before_driver_account_id INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 更换前司机
        before_vehicle_id        INTEGER REFERENCES vehicles(id) ON DELETE RESTRICT, -- 更换前车辆
        after_driver_account_id  INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 更换后司机
        after_vehicle_id         INTEGER REFERENCES vehicles(id) ON DELETE RESTRICT, -- 更换后车辆
        before_deliver_at        TEXT, -- 调整前计划送达时间，ISO 8601
        after_deliver_at         TEXT, -- 调整后计划送达时间，ISO 8601
        order_status             TEXT NOT NULL CHECK(order_status IN ('待承接','已承接','运输中','已完成','取消处理中','已取消','异常处理中')), -- 处理后订单状态
        task_status              TEXT NOT NULL CHECK(task_status IN ('待司机确认','待装货','运输中','待签收','待确认完成','已完成','异常','已拒绝','已取消')), -- 处理后任务状态投影
        reason                   TEXT NOT NULL DEFAULT '', -- 变更原因
        handled_at               TEXT NOT NULL, -- 处理时间，ISO 8601
        replaced_by              INTEGER REFERENCES exception_handling_records(id) ON DELETE RESTRICT, -- 更正记录
        created_at               TEXT NOT NULL -- 记录时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_anomalies_task ON transport_anomalies(task_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_anomalies_order ON transport_anomalies(order_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_anomaly_handling ON exception_handling_records(anomaly_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_handling_task ON exception_handling_records(task_id, id)",
    "CREATE TRIGGER IF NOT EXISTS trg_anomalies_no_update BEFORE UPDATE ON transport_anomalies BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_anomalies_no_delete BEFORE DELETE ON transport_anomalies BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_handling_no_update BEFORE UPDATE ON exception_handling_records BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_handling_no_delete BEFORE DELETE ON exception_handling_records BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
]


def migrate_exception(conn: sqlite3.Connection) -> None:
    """在已开启的事务内创建在途异常与处理记录表、索引和不可变触发器。"""
    for statement in _EXCEPTION_SCHEMA:
        conn.execute(statement)
