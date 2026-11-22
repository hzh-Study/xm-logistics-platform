"""报销费用提交、审核与支付标记迁移（v14）：费用、凭证与追加式状态历史。

费用与凭证为不可变业务记录；审核与支付均以事件形式追加，两条状态互不改写。
"""

import sqlite3

_EXPENSE_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS expenses (
        id                 INTEGER PRIMARY KEY,
        expense_no         TEXT NOT NULL UNIQUE, -- 报销费用编号，FE-YYMMDD-0001
        task_id            INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        order_id           INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT, -- 所属运输订单
        driver_account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 提交司机
        carrier_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 审核物流公司
        expense_type       TEXT NOT NULL CHECK(expense_type IN ('油费','过路费','停车费','维修费','其他')), -- 费用类型
        amount_cents       INTEGER NOT NULL CHECK(amount_cents > 0), -- 金额，单位：分
        incurred_at        TEXT NOT NULL, -- 费用发生时间，ISO 8601
        description        TEXT NOT NULL, -- 费用说明
        replaced_by        INTEGER REFERENCES expenses(id) ON DELETE RESTRICT, -- 本笔替代的原驳回费用
        actor              TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        created_at         TEXT NOT NULL -- 提交时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS expense_vouchers (
        id          INTEGER PRIMARY KEY,
        expense_id  INTEGER NOT NULL REFERENCES expenses(id) ON DELETE RESTRICT, -- 所属报销费用
        path        TEXT NOT NULL, -- 凭证库内相对路径
        actor       TEXT NOT NULL DEFAULT '司机', -- 上传角色
        replaced_by INTEGER REFERENCES expense_vouchers(id) ON DELETE RESTRICT, -- 更正记录
        created_at  TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS expense_history (
        id          INTEGER PRIMARY KEY,
        expense_id  INTEGER NOT NULL REFERENCES expenses(id) ON DELETE RESTRICT, -- 所属报销费用
        event       TEXT NOT NULL CHECK(event IN ('提交','审核通过','审核驳回','标记已支付','重新提交')), -- 状态事件
        reason      TEXT NOT NULL DEFAULT '', -- 驳回原因或事件说明
        actor       TEXT NOT NULL CHECK(actor IN ('司机','物流公司')), -- 操作角色
        actor_id    INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 操作人账号
        replaced_by INTEGER REFERENCES expense_history(id) ON DELETE RESTRICT, -- 更正记录
        created_at  TEXT NOT NULL -- 事件时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_expenses_carrier ON expenses(carrier_account_id, created_at, id)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_driver ON expenses(driver_account_id, created_at, id)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_task ON expenses(task_id, replaced_by, id)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_no ON expenses(expense_no)",
    "CREATE INDEX IF NOT EXISTS idx_expense_vouchers_expense ON expense_vouchers(expense_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_expense_history_expense ON expense_history(expense_id, id, event)",
    "CREATE TRIGGER IF NOT EXISTS trg_expenses_no_update BEFORE UPDATE ON expenses BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_expenses_no_delete BEFORE DELETE ON expenses BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_expense_vouchers_no_update BEFORE UPDATE ON expense_vouchers BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_expense_vouchers_no_delete BEFORE DELETE ON expense_vouchers BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_expense_history_no_update BEFORE UPDATE ON expense_history BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_expense_history_no_delete BEFORE DELETE ON expense_history BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
]


def migrate_expense(conn: sqlite3.Connection) -> None:
    """在已开启的事务内创建报销费用相关表、索引与不可变触发器。"""
    for statement in _EXPENSE_SCHEMA:
        conn.execute(statement)
