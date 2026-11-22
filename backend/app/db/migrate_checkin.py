"""打卡与起运迁移（v10）：发货快照坐标、打卡/装货凭证/起运确认表。

业务记录一律追加不可变；发货快照坐标起运后锁定，不回写历史。
"""

import sqlite3

def _add_column_if_missing(conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    """幂等追加列：列已存在时跳过。"""
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


_CHECKIN_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS departure_checkins (
        id                INTEGER PRIMARY KEY,
        task_id           INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        order_id          INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT, -- 所属运输订单
        driver_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 打卡司机
        latitude          REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90), -- 定位纬度
        longitude         REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180), -- 定位经度
        arrived_at        TEXT NOT NULL, -- 到达时间，ISO 8601
        photos            TEXT NOT NULL DEFAULT '[]', -- 现场照片相对路径 JSON 数组
        notes             TEXT NOT NULL DEFAULT '', -- 司机备注
        position_status   TEXT NOT NULL CHECK(position_status IN ('正常','位置异常')), -- 位置判定
        distance_m        INTEGER, -- 与发货快照直线距离，单位：米；无坐标为 NULL
        reason            TEXT NOT NULL DEFAULT '', -- 记录或更正原因
        actor             TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by       INTEGER REFERENCES departure_checkins(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL, -- 创建时间，ISO 8601
        CHECK(distance_m IS NULL OR distance_m >= 0)
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS checkin_exception_notes (
        id          INTEGER PRIMARY KEY,
        checkin_id  INTEGER NOT NULL REFERENCES departure_checkins(id) ON DELETE RESTRICT, -- 关联打卡
        note        TEXT NOT NULL, -- 位置异常说明
        actor       TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by INTEGER REFERENCES checkin_exception_notes(id) ON DELETE RESTRICT, -- 更正记录
        created_at  TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS loading_photos (
        id                INTEGER PRIMARY KEY,
        task_id           INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        driver_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 上传司机
        phase             TEXT NOT NULL CHECK(phase IN ('装货前','装货中','装货完成')), -- 装货阶段
        paths             TEXT NOT NULL, -- 现场照片相对路径 JSON 数组
        actor             TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by       INTEGER REFERENCES loading_photos(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS loading_anomalies (
        id                INTEGER PRIMARY KEY,
        task_id           INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        driver_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 上报司机
        kind              TEXT NOT NULL CHECK(kind IN ('数量不符','货损','超载')), -- 装货异常类型
        detail            TEXT NOT NULL, -- 异常详情
        photos            TEXT NOT NULL DEFAULT '[]', -- 异常照片相对路径 JSON 数组
        actor             TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by       INTEGER REFERENCES loading_anomalies(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS departure_confirmations (
        id                INTEGER PRIMARY KEY,
        task_id           INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        driver_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 确认司机
        cargo_confirmed   INTEGER NOT NULL CHECK(cargo_confirmed IN (0,1)), -- 货物核对完成：0/1
        vehicle_confirmed INTEGER NOT NULL CHECK(vehicle_confirmed IN (0,1)), -- 车辆核对完成：0/1
        notes             TEXT NOT NULL DEFAULT '', -- 起运备注
        actor             TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by       INTEGER REFERENCES departure_confirmations(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_checkins_task ON departure_checkins(task_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_checkin_notes_checkin ON checkin_exception_notes(checkin_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_loading_photos_task ON loading_photos(task_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_loading_anomalies_task ON loading_anomalies(task_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_departure_confirmations_task ON departure_confirmations(task_id, replaced_by, id)",
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_site_coord_locked
    BEFORE UPDATE OF ship_lat, ship_lon ON orders
    WHEN OLD.status NOT IN ('待承接','已承接')
    BEGIN SELECT RAISE(ABORT, 'shipping site coordinate is immutable'); END
    """,
    "CREATE TRIGGER IF NOT EXISTS trg_departure_checkins_no_update BEFORE UPDATE ON departure_checkins BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_departure_checkins_no_delete BEFORE DELETE ON departure_checkins BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_checkin_notes_no_update BEFORE UPDATE ON checkin_exception_notes BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_checkin_notes_no_delete BEFORE DELETE ON checkin_exception_notes BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_loading_photos_no_update BEFORE UPDATE ON loading_photos BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_loading_photos_no_delete BEFORE DELETE ON loading_photos BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_loading_anomalies_no_update BEFORE UPDATE ON loading_anomalies BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_loading_anomalies_no_delete BEFORE DELETE ON loading_anomalies BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_departure_confirmations_no_update BEFORE UPDATE ON departure_confirmations BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_departure_confirmations_no_delete BEFORE DELETE ON departure_confirmations BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
]


def migrate_checkin(conn: sqlite3.Connection) -> None:
    """在已开启的事务内创建打卡与起运相关表与索引。"""
    # 发货快照纬度 / 经度：起运前由货主补录，起运后由触发器锁定
    _add_column_if_missing(conn, "orders", "ship_lat", "ship_lat REAL")
    _add_column_if_missing(conn, "orders", "ship_lon", "ship_lon REAL")
    for statement in _CHECKIN_SCHEMA:
        conn.execute(statement)
