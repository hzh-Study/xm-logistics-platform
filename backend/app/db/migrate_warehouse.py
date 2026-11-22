"""仓库主数据迁移（v4）：仓库为可变主数据，停用用状态表达，不做物理删除。"""

import sqlite3

_WAREHOUSE_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS warehouses (
        id             INTEGER PRIMARY KEY,
        shipper_id     INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 所属货主
        name           TEXT NOT NULL,  -- 仓库名称
        contact        TEXT NOT NULL,  -- 仓库联系人
        phone          TEXT NOT NULL,  -- 联系电话
        province       TEXT NOT NULL,  -- 所在省份
        city           TEXT NOT NULL,  -- 所在城市
        district       TEXT NOT NULL,  -- 所在区县
        detail_address TEXT NOT NULL,  -- 详细地址
        type           TEXT NOT NULL,  -- 仓库类型
        remarks        TEXT NOT NULL DEFAULT '', -- 仓库备注
        status         TEXT NOT NULL DEFAULT '正常' CHECK(status IN ('正常','停用')), -- 仓库状态
        created_at     TEXT NOT NULL,  -- 创建时间，ISO 8601
        updated_at     TEXT NOT NULL   -- 修改时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_warehouses_shipper_status ON warehouses(shipper_id, status, id)",
    "CREATE INDEX IF NOT EXISTS idx_warehouses_shipper_name ON warehouses(shipper_id, name, id)",
]


def migrate_warehouse(conn: sqlite3.Connection) -> None:
    """在已开启的事务内创建仓库表与列表筛选索引。"""
    for statement in _WAREHOUSE_SCHEMA:
        conn.execute(statement)
