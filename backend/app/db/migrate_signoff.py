"""收货地打卡、卸货与签收完成迁移（v12）：到达打卡/卸货凭证/签收凭证表。

业务记录一律追加不可变；收货快照坐标送达前可补录，运输开始后由触发器锁定。
"""

import sqlite3


def _add_column_if_missing(conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    """幂等追加列：列已存在时跳过。"""
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


_SIGNOFF_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS arrival_checkins (
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
        distance_m        INTEGER, -- 与收货快照直线距离，单位：米；无坐标为 NULL
        reason            TEXT NOT NULL DEFAULT '', -- 记录或更正原因
        actor             TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by       INTEGER REFERENCES arrival_checkins(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL, -- 创建时间，ISO 8601
        CHECK(distance_m IS NULL OR distance_m >= 0)
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS arrival_exception_notes (
        id          INTEGER PRIMARY KEY,
        checkin_id  INTEGER NOT NULL REFERENCES arrival_checkins(id) ON DELETE RESTRICT, -- 关联打卡
        note        TEXT NOT NULL, -- 位置异常说明
        actor       TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by INTEGER REFERENCES arrival_exception_notes(id) ON DELETE RESTRICT, -- 更正记录
        created_at  TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS unloading_photos (
        id                INTEGER PRIMARY KEY,
        task_id           INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        driver_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 上传司机
        phase             TEXT NOT NULL CHECK(phase IN ('卸货前','卸货中','卸货完成')), -- 卸货阶段
        paths             TEXT NOT NULL, -- 现场照片相对路径 JSON 数组
        actor             TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by       INTEGER REFERENCES unloading_photos(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS unloading_anomalies (
        id                INTEGER PRIMARY KEY,
        task_id           INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        driver_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 上报司机
        kind              TEXT NOT NULL CHECK(kind IN ('货损','数量不符','拒收')), -- 卸货异常类型
        detail            TEXT NOT NULL, -- 异常详情
        photos            TEXT NOT NULL DEFAULT '[]', -- 异常照片相对路径 JSON 数组
        actor             TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by       INTEGER REFERENCES unloading_anomalies(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS signoff_vouchers (
        id                  INTEGER PRIMARY KEY,
        voucher_no          TEXT NOT NULL UNIQUE, -- 签收凭证号，SIGN-YYMMDD-0001
        task_id             INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        order_id            INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT, -- 所属运输订单
        driver_account_id   INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 提交司机
        receiving_condition TEXT NOT NULL CHECK(receiving_condition IN ('完好','货损','数量不符','其他')), -- 收货情况
        received_at         TEXT NOT NULL, -- 收货时间，ISO 8601
        receiver_name       TEXT NOT NULL, -- 收货人
        signature_photos    TEXT NOT NULL DEFAULT '[]', -- 签收照片相对路径 JSON 数组
        vouchers            TEXT NOT NULL DEFAULT '[]', -- 凭证相对路径 JSON 数组
        notes               TEXT NOT NULL DEFAULT '', -- 司机备注
        actor               TEXT NOT NULL DEFAULT '司机', -- 记录发起角色
        replaced_by         INTEGER REFERENCES signoff_vouchers(id) ON DELETE RESTRICT, -- 更正记录
        created_at          TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS signoff_confirmations (
        id                INTEGER PRIMARY KEY,
        task_id           INTEGER NOT NULL REFERENCES transport_tasks(id) ON DELETE RESTRICT, -- 所属运输任务
        voucher_id        INTEGER NOT NULL REFERENCES signoff_vouchers(id) ON DELETE RESTRICT, -- 据以确认的签收凭证
        carrier_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 确认公司账号
        notes             TEXT NOT NULL DEFAULT '', -- 确认备注
        actor             TEXT NOT NULL DEFAULT '物流公司', -- 记录发起角色
        replaced_by       INTEGER REFERENCES signoff_confirmations(id) ON DELETE RESTRICT, -- 更正记录
        created_at        TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_arrival_checkins_task ON arrival_checkins(task_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_arrival_notes_checkin ON arrival_exception_notes(checkin_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_unloading_photos_task ON unloading_photos(task_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_unloading_anomalies_task ON unloading_anomalies(task_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_signoff_vouchers_task ON signoff_vouchers(task_id, replaced_by, id)",
    "CREATE INDEX IF NOT EXISTS idx_signoff_confirmations_task ON signoff_confirmations(task_id, replaced_by, id)",
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_recv_coord_locked
    BEFORE UPDATE OF recv_lat, recv_lon ON orders
    WHEN OLD.status NOT IN ('待承接','已承接')
    BEGIN SELECT RAISE(ABORT, 'receiving site coordinate is immutable'); END
    """,
    "CREATE TRIGGER IF NOT EXISTS trg_arrival_checkins_no_update BEFORE UPDATE ON arrival_checkins BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_arrival_checkins_no_delete BEFORE DELETE ON arrival_checkins BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_arrival_notes_no_update BEFORE UPDATE ON arrival_exception_notes BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_arrival_notes_no_delete BEFORE DELETE ON arrival_exception_notes BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_unloading_photos_no_update BEFORE UPDATE ON unloading_photos BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_unloading_photos_no_delete BEFORE DELETE ON unloading_photos BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_unloading_anomalies_no_update BEFORE UPDATE ON unloading_anomalies BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_unloading_anomalies_no_delete BEFORE DELETE ON unloading_anomalies BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_signoff_vouchers_no_update BEFORE UPDATE ON signoff_vouchers BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_signoff_vouchers_no_delete BEFORE DELETE ON signoff_vouchers BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_signoff_confirmations_no_update BEFORE UPDATE ON signoff_confirmations BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_signoff_confirmations_no_delete BEFORE DELETE ON signoff_confirmations BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
]


def migrate_signoff(conn: sqlite3.Connection) -> None:
    """在已开启的事务内创建收货地打卡与签收相关表与索引。"""
    # 收货快照纬度 / 经度：运输前由货主补录，起运后由触发器锁定
    _add_column_if_missing(conn, "orders", "recv_lat", "recv_lat REAL")
    _add_column_if_missing(conn, "orders", "recv_lon", "recv_lon REAL")
    for statement in _SIGNOFF_SCHEMA:
        conn.execute(statement)
