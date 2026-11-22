"""车辆表迁移（v8）：可用性与生命周期两维独立，车辆不物理删除。"""

import sqlite3

_VEHICLE_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS vehicles (
        id                INTEGER PRIMARY KEY,
        plate_no          TEXT NOT NULL UNIQUE, -- 车牌号
        carrier_id        INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 所属物流公司
        vehicle_type      TEXT NOT NULL CHECK(vehicle_type IN ('厢式货车','平板货车','高栏货车','冷藏车','其他')), -- 车辆类型
        length_m          REAL NOT NULL CHECK(length_m > 0), -- 车长，米
        max_load_kg       INTEGER NOT NULL CHECK(max_load_kg > 0), -- 最大载重，千克
        owner_type        TEXT NOT NULL CHECK(owner_type IN ('公司','司机')), -- 实际所有者类型
        owner_driver_id   INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 车主司机，个人车辆必填
        current_driver_id INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 当前司机，公司车辆分配后写入
        availability      TEXT NOT NULL DEFAULT '可用' CHECK(availability IN ('可用','占用中','暂停使用')), -- 可用性，独立于生命周期
        lifecycle         TEXT NOT NULL DEFAULT '在册' CHECK(lifecycle IN ('在册','维修中','已停用')), -- 生命周期，独立于可用性
        document_status   TEXT NOT NULL DEFAULT '待审核' CHECK(document_status IN ('待审核','有效','已过期')), -- 证件状态
        created_at        TEXT NOT NULL, -- 创建时间，ISO 8601
        updated_at        TEXT NOT NULL  -- 更新时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_vehicles_carrier ON vehicles(carrier_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_vehicles_carrier_availability ON vehicles(carrier_id, availability)",
    "CREATE INDEX IF NOT EXISTS idx_vehicles_carrier_lifecycle ON vehicles(carrier_id, lifecycle)",
    "CREATE INDEX IF NOT EXISTS idx_vehicles_current_driver ON vehicles(current_driver_id, carrier_id)",
]


def migrate_vehicle(conn: sqlite3.Connection) -> None:
    """在已开启的事务内创建车辆表与列表索引。"""
    for statement in _VEHICLE_SCHEMA:
        conn.execute(statement)
