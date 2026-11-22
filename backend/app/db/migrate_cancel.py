"""订单取消与终止运输迁移（v13）：取消申请当前态与追加不可变的操作留痕。

取消申请的每一次申请、直接取消、同意与驳回都追加审计记录，原记录不覆盖；
任务侧只增一个取消投影列，不改运输任务状态枚举，也不触碰收发快照与坐标。
"""

import sqlite3

_CANCEL_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS cancel_applications (
        id              INTEGER PRIMARY KEY,
        application_no  TEXT NOT NULL UNIQUE, -- 取消申请号，CANC-YYMMDD-0001
        order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT, -- 所属运输订单
        shipper_id      INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 申请货主
        carrier_id      INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 承运物流公司，承接后才有
        mode            TEXT NOT NULL CHECK(mode IN ('直接取消','公司确认')), -- 取消方式
        status          TEXT NOT NULL CHECK(status IN ('待公司处理','已同意','已驳回','已直接取消')), -- 申请状态
        reason          TEXT NOT NULL DEFAULT '', -- 货主申请原因
        handled_reason  TEXT NOT NULL DEFAULT '', -- 公司驳回原因
        before_status   TEXT NOT NULL CHECK(before_status IN ('待承接','已承接','运输中','已完成','取消处理中','已取消','异常处理中')), -- 申请前订单状态
        after_status    TEXT CHECK(after_status IN ('待承接','已承接','运输中','已完成','取消处理中','已取消','异常处理中')), -- 处理后订单状态
        handled_by      INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 处理人账号
        handled_at      TEXT, -- 处理时间，ISO 8601
        created_at      TEXT NOT NULL, -- 申请时间，ISO 8601
        updated_at      TEXT NOT NULL  -- 状态更新时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS cancel_audit (
        id              INTEGER PRIMARY KEY,
        application_id  INTEGER NOT NULL REFERENCES cancel_applications(id) ON DELETE RESTRICT, -- 所属取消申请
        order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT, -- 所属运输订单
        event           TEXT NOT NULL CHECK(event IN ('申请','直接取消','同意','驳回')), -- 操作事件
        actor_id        INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 操作人账号
        actor           TEXT NOT NULL CHECK(actor IN ('货主','物流公司')), -- 操作人角色
        from_status     TEXT NOT NULL CHECK(from_status IN ('待承接','已承接','运输中','已完成','取消处理中','已取消','异常处理中')), -- 变更前订单状态
        to_status       TEXT NOT NULL CHECK(to_status IN ('待承接','已承接','运输中','已完成','取消处理中','已取消','异常处理中')), -- 变更后订单状态
        reason          TEXT NOT NULL DEFAULT '', -- 操作原因
        detail          TEXT NOT NULL DEFAULT '', -- 操作说明
        created_at      TEXT NOT NULL, -- 留痕时间，ISO 8601
        replaced_by     INTEGER REFERENCES cancel_audit(id) ON DELETE RESTRICT -- 更正记录
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_cancel_apps_order ON cancel_applications(order_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_cancel_apps_carrier ON cancel_applications(carrier_id, status, id)",
    "CREATE INDEX IF NOT EXISTS idx_cancel_audit_app ON cancel_audit(application_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_cancel_audit_order ON cancel_audit(order_id, id)",
    "-- 取消申请只追加、不物理删除；状态沿生命周期更新\nCREATE TRIGGER IF NOT EXISTS trg_cancel_apps_no_delete BEFORE DELETE ON cancel_applications BEGIN SELECT RAISE(ABORT, 'cancel application is read-only for deletion'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_cancel_audit_no_update BEFORE UPDATE ON cancel_audit BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_cancel_audit_no_delete BEFORE DELETE ON cancel_audit BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "-- 状态类投影：取消中的任务在任务侧留一列，不改 transport_tasks.status 枚举\nALTER TABLE transport_tasks ADD COLUMN cancel_status TEXT NOT NULL DEFAULT '' CHECK(cancel_status IN ('','取消中','已取消'))",
    """
    CREATE TRIGGER IF NOT EXISTS trg_cancel_exception_exclusive
    BEFORE UPDATE OF status ON orders
    WHEN NEW.status = '异常处理中'
     AND EXISTS (
         SELECT 1 FROM cancel_applications a
         WHERE a.order_id = NEW.id AND a.status = '待公司处理'
     )
    BEGIN SELECT RAISE(ABORT, '取消处理中与异常处理中互斥'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_terminate_task_cancel_projection
    AFTER INSERT ON exception_handling_records
    WHEN NEW.result = '终止运输'
    BEGIN UPDATE transport_tasks SET cancel_status = '已取消' WHERE id = NEW.task_id; END
    """,
]


def migrate_cancel(conn: sqlite3.Connection) -> None:
    """在已开启的事务内创建取消申请表、审计表、索引与互斥触发器。"""
    for statement in _CANCEL_SCHEMA:
        conn.execute(statement)
