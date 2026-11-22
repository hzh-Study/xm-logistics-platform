"""版本化迁移：版本号存 user_version，迁移与递增在同一事务。"""

import sqlite3

LATEST_VERSION = 12

_SCHEMA = [
    """
    CREATE TABLE accounts (
        id             INTEGER PRIMARY KEY,
        phone          TEXT NOT NULL UNIQUE, -- 登录手机号
        role           TEXT NOT NULL CHECK(role IN ('货主','物流公司','司机','管理员')), -- 角色
        account_status TEXT NOT NULL CHECK(account_status IN ('正常使用','已禁用','已注销')), -- 账号状态
        auth_status    TEXT NOT NULL CHECK(auth_status IN ('未提交','待审核','审核通过','审核不通过')), -- 认证状态
        password_hash  TEXT NOT NULL,
        created_at     TEXT NOT NULL         -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE shipper_profiles (
        account_id   INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE RESTRICT,
        profile_type TEXT NOT NULL DEFAULT '' CHECK(profile_type IN ('','个人','企业')), -- 货主认证类型
        company_name TEXT NOT NULL DEFAULT ''
    ) STRICT
    """,
    """
    CREATE TABLE carrier_profiles (
        account_id   INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE RESTRICT,
        company_name TEXT NOT NULL DEFAULT '',
        license_no   TEXT NOT NULL DEFAULT ''
    ) STRICT
    """,
    """
    CREATE TABLE driver_profiles (
        account_id    INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE RESTRICT,
        carrier_id    INTEGER REFERENCES accounts(id) ON DELETE RESTRICT, -- 所属物流公司
        license_no    TEXT NOT NULL DEFAULT ''
    ) STRICT
    """,
    """
    CREATE TABLE admin_profiles (
        account_id   INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE RESTRICT,
        display_name TEXT NOT NULL DEFAULT ''
    ) STRICT
    """,
    """
    CREATE TABLE sessions (
        token_hash TEXT PRIMARY KEY,     -- token 的 SHA-256 摘要
        account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
        role       TEXT NOT NULL CHECK(role IN ('货主','物流公司','司机','管理员')),
        csrf_token TEXT NOT NULL,
        expires_at TEXT NOT NULL,        -- ISO 8601
        revoked_at TEXT,                 -- 撤销时间，ISO 8601
        created_at TEXT NOT NULL         -- ISO 8601
    ) STRICT
    """,
    "CREATE INDEX idx_sessions_account ON sessions(account_id)",
]

# 货主认证闭环：提交记录与审核记录均追加不可变，通知只落站内记录。
_V2 = [
    """
    CREATE TABLE shipper_certifications (
        id            INTEGER PRIMARY KEY,
        account_id    INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
        cert_type     TEXT NOT NULL CHECK(cert_type IN ('个人','企业')), -- 认证类型
        name          TEXT NOT NULL,  -- 个人姓名或企业名称
        id_number     TEXT NOT NULL,  -- 身份证号或统一社会信用代码
        contact_phone TEXT NOT NULL,  -- 联系人电话
        documents     TEXT NOT NULL,  -- 资料相对路径 JSON 数组
        created_at    TEXT NOT NULL   -- 提交时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE shipper_cert_reviews (
        id               INTEGER PRIMARY KEY,
        certification_id INTEGER NOT NULL REFERENCES shipper_certifications(id) ON DELETE RESTRICT,
        decision         TEXT NOT NULL CHECK(decision IN ('审核通过','审核不通过')), -- 审核结论
        reason           TEXT NOT NULL DEFAULT '', -- 驳回原因，审核不通过时必填
        actor_id         INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT, -- 审核人
        created_at       TEXT NOT NULL, -- 审核时间，ISO 8601
        replaced_by      INTEGER REFERENCES shipper_cert_reviews(id) ON DELETE RESTRICT -- 更正记录
    ) STRICT
    """,
    """
    CREATE TABLE notifications (
        id            INTEGER PRIMARY KEY,
        recipient_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
        recipient_role TEXT NOT NULL CHECK(recipient_role IN ('货主','物流公司','司机','管理员')), -- 收件人角色
        kind          TEXT NOT NULL, -- 通知类型
        title         TEXT NOT NULL, -- 通知标题
        body          TEXT NOT NULL, -- 通知正文
        related_id    INTEGER,  -- 关联业务记录 id
        created_at    TEXT NOT NULL -- 创建时间，ISO 8601
    ) STRICT
    """,
    """
    CREATE TABLE orders (
        id          INTEGER PRIMARY KEY,
        order_no    TEXT NOT NULL UNIQUE, -- 运输订单号，prefix-YYMMDD-0001
        shipper_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
        cargo_name  TEXT NOT NULL,  -- 货物名称
        status      TEXT NOT NULL DEFAULT '待承接'
            CHECK(status IN ('待承接','已承接','运输中','已完成','取消处理中','已取消','异常处理中')), -- 运输订单状态
        created_at  TEXT NOT NULL   -- 发布时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX idx_shipper_certs_account ON shipper_certifications(account_id)",
    "CREATE INDEX idx_shipper_cert_reviews_cert ON shipper_cert_reviews(certification_id)",
    "CREATE INDEX idx_notifications_recipient ON notifications(recipient_id)",
    "CREATE INDEX idx_orders_shipper ON orders(shipper_id)",
    "CREATE INDEX idx_orders_no ON orders(order_no)",
    "CREATE TRIGGER trg_shipper_cert_immutable BEFORE UPDATE ON shipper_certifications BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER trg_shipper_cert_no_delete BEFORE DELETE ON shipper_certifications BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER trg_shipper_review_immutable BEFORE UPDATE ON shipper_cert_reviews BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER trg_shipper_review_no_delete BEFORE DELETE ON shipper_cert_reviews BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
]

# 司机创建与身份绑定（v7）：司机基本资料可改，身份与驾驶资格提交只读追加。
_V7 = [
    "-- 司机姓名\nALTER TABLE driver_profiles ADD COLUMN name TEXT NOT NULL DEFAULT ''",
    "-- 身份证号\nALTER TABLE driver_profiles ADD COLUMN id_number TEXT NOT NULL DEFAULT ''",
    "-- 准驾车型\nALTER TABLE driver_profiles ADD COLUMN license_type TEXT NOT NULL DEFAULT ''",
    "-- 驾驶证有效期，ISO 8601\nALTER TABLE driver_profiles ADD COLUMN license_expiry TEXT NOT NULL DEFAULT ''",
    "-- 接单可用性：可派单/任务占用中/暂停接单\nALTER TABLE driver_profiles ADD COLUMN availability TEXT NOT NULL DEFAULT '可派单' CHECK(availability IN ('可派单','任务占用中','暂停接单'))",
    "-- 雇佣关系：在职/离职\nALTER TABLE driver_profiles ADD COLUMN employment TEXT NOT NULL DEFAULT '在职' CHECK(employment IN ('在职','离职'))",
    "-- 离职日期，ISO 8601\nALTER TABLE driver_profiles ADD COLUMN departure_date TEXT",
    "-- 是否强制修改初始密码\nALTER TABLE driver_profiles ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 1 CHECK(must_change_password IN (0,1))",
    "-- 身份绑定是否完成\nALTER TABLE driver_profiles ADD COLUMN binding_complete INTEGER NOT NULL DEFAULT 0 CHECK(binding_complete IN (0,1))",
    """
    CREATE TABLE driver_identity_history (
        id            INTEGER PRIMARY KEY,
        account_id    INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
        name          TEXT NOT NULL,  -- 姓名快照
        id_number     TEXT NOT NULL,  -- 身份证号快照
        license_no    TEXT NOT NULL,  -- 驾驶证号快照
        license_type  TEXT NOT NULL,  -- 准驾车型快照
        license_expiry TEXT NOT NULL, -- 驾驶证有效期快照，ISO 8601
        reason        TEXT NOT NULL,  -- 提交或变更原因
        actor         TEXT NOT NULL,  -- 记录发起角色
        replaced_by   INTEGER REFERENCES driver_identity_history(id) ON DELETE RESTRICT, -- 本记录替代的前序记录
        created_at    TEXT NOT NULL   -- 创建时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX idx_driver_identity_account ON driver_identity_history(account_id, id)",
    "CREATE TRIGGER trg_driver_identity_no_update BEFORE UPDATE ON driver_identity_history BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
    "CREATE TRIGGER trg_driver_identity_no_delete BEFORE DELETE ON driver_identity_history BEGIN SELECT RAISE(ABORT, 'immutable history'); END",
]

_PROFILE_TABLES = {
    "货主": "shipper_profiles",
    "物流公司": "carrier_profiles",
    "司机": "driver_profiles",
    "管理员": "admin_profiles",
}


def migrate(conn: sqlite3.Connection) -> None:
    """按版本顺序迁移到最新版本。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version > LATEST_VERSION:
            raise RuntimeError(f"库版本 {version} 高于代码可识别版本 {LATEST_VERSION}")
        if version < 1:
            for statement in _SCHEMA:
                conn.execute(statement)
            conn.execute("PRAGMA user_version = 1")
        if version < 2:
            for statement in _V2:
                conn.execute(statement)
            conn.execute("PRAGMA user_version = 2")
        if version < 3:
            from app.db.migrate_carrier import migrate_carrier

            migrate_carrier(conn)
            conn.execute("PRAGMA user_version = 3")
        if version < 4:
            from app.db.migrate_warehouse import migrate_warehouse

            migrate_warehouse(conn)
            conn.execute("PRAGMA user_version = 4")
        if version < 5:
            from app.db.migrate_order import migrate_order

            migrate_order(conn)
            conn.execute("PRAGMA user_version = 5")
        if version < 6:
            from app.db.migrate_order_pool import migrate_order_pool

            migrate_order_pool(conn)
            conn.execute("PRAGMA user_version = 6")
        if version < 7:
            for statement in _V7:
                conn.execute(statement)
            conn.execute("PRAGMA user_version = 7")
        if version < 8:
            from app.db.migrate_vehicle import migrate_vehicle

            migrate_vehicle(conn)
            conn.execute("PRAGMA user_version = 8")
        if version < 9:
            from app.db.migrate_dispatch import migrate_dispatch

            migrate_dispatch(conn)
            conn.execute("PRAGMA user_version = 9")
        if version < 10:
            from app.db.migrate_checkin import migrate_checkin

            migrate_checkin(conn)
            conn.execute("PRAGMA user_version = 10")
        # NOTE: v12 须排在 v11（在途异常）之后；合并 #12 时勿调换两个代码块的先后顺序。
        if version < 12:
            from app.db.migrate_signoff import migrate_signoff

            migrate_signoff(conn)
            conn.execute("PRAGMA user_version = 12")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def profile_table_for(role: str) -> str:
    """返回角色对应的 profile 表名。"""
    return _PROFILE_TABLES[role]
