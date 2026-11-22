"""管理员平台迁移（v15）：公告/通知独立内容通道、统一审核留痕与审核状态列。"""

import sqlite3

_ADMIN_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS announcements (
        id            INTEGER PRIMARY KEY,
        title         TEXT NOT NULL,  -- 公告标题
        body          TEXT NOT NULL,  -- 公告正文
        scope         TEXT NOT NULL DEFAULT '全部'
            CHECK(scope IN ('全部','货主','物流公司','司机')), -- 可见范围
        publisher_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 发布管理员
        published_at  TEXT NOT NULL,  -- 发布时间，ISO 8601
        channel       TEXT NOT NULL DEFAULT '平台公告' CHECK(channel IN ('平台公告')) -- 内容通道，非业务事件
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS notices (
        id            INTEGER PRIMARY KEY,
        title         TEXT NOT NULL,  -- 通知标题
        body          TEXT NOT NULL,  -- 通知正文
        scope         TEXT NOT NULL DEFAULT '全部'
            CHECK(scope IN ('全部','货主','物流公司','司机')), -- 可见范围
        publisher_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 发布管理员
        published_at  TEXT NOT NULL,  -- 发布时间，ISO 8601
        channel       TEXT NOT NULL DEFAULT '平台通知' CHECK(channel IN ('平台通知')) -- 内容通道，非业务事件
    ) STRICT
    """,
    """
    CREATE TABLE IF NOT EXISTS admin_cert_reviews (
        id            INTEGER PRIMARY KEY,
        category      TEXT NOT NULL
            CHECK(category IN ('货主','企业','司机','驾驶资格','车辆证件')), -- 认证类别
        target_id     INTEGER NOT NULL,  -- 目标记录或账号 id
        decision      TEXT NOT NULL CHECK(decision IN ('审核通过','审核不通过')), -- 审核结论
        reason        TEXT NOT NULL DEFAULT '',  -- 驳回原因，审核不通过时必填
        actor_id      INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 审核管理员
        replaced_by   INTEGER REFERENCES admin_cert_reviews(id) ON DELETE RESTRICT, -- 更正记录
        created_at    TEXT NOT NULL    -- 审核时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_announcements_published ON announcements(published_at, id)",
    "CREATE INDEX IF NOT EXISTS idx_notices_published ON notices(published_at, id)",
    "CREATE INDEX IF NOT EXISTS idx_admin_cert_reviews_target ON admin_cert_reviews(category, target_id, id)",
    "CREATE TRIGGER IF NOT EXISTS trg_admin_cert_reviews_no_update BEFORE UPDATE ON admin_cert_reviews BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER IF NOT EXISTS trg_admin_cert_reviews_no_delete BEFORE DELETE ON admin_cert_reviews BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
]

_QUALIFICATION_COLUMN = (
    "-- 驾驶资格审核状态\nALTER TABLE driver_profiles ADD COLUMN qualification_status "
    "TEXT NOT NULL DEFAULT '待审核' "
    "CHECK(qualification_status IN ('待审核','有效','审核不通过'))"
)

_VEHICLE_DOC_COLUMN = (
    "-- 车辆证件审核结论，独立于证件有效性\nALTER TABLE vehicles ADD COLUMN document_review_status "
    "TEXT NOT NULL DEFAULT '待审核' "
    "CHECK(document_review_status IN ('待审核','有效','驳回'))"
)


def migrate_admin(conn: sqlite3.Connection) -> None:
    """在已开启的事务内幂等创建管理员平台表与审核状态列。"""
    for statement in _ADMIN_SCHEMA:
        conn.execute(statement)
    driver_columns = {row[1] for row in conn.execute("PRAGMA table_info(driver_profiles)")}
    if "qualification_status" not in driver_columns:
        conn.execute(_QUALIFICATION_COLUMN)
    vehicle_columns = {row[1] for row in conn.execute("PRAGMA table_info(vehicles)")}
    if "document_review_status" not in vehicle_columns:
        conn.execute(_VEHICLE_DOC_COLUMN)
