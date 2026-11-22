"""物流公司认证表迁移（v2）：认证记录只读追加，带不可变触发器。"""

import sqlite3

_CARRIER_CERT_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS carrier_certifications (
        id                INTEGER PRIMARY KEY,
        account_id        INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
        kind              TEXT NOT NULL CHECK(kind IN ('提交','审核')), -- 记录类型：提交/审核
        decision          TEXT NOT NULL DEFAULT '' CHECK(decision IN ('','通过','驳回')), -- 审核结论
        company_name      TEXT NOT NULL DEFAULT '', -- 企业名称快照
        license_no        TEXT NOT NULL DEFAULT '', -- 营业执照号快照
        license_path      TEXT NOT NULL DEFAULT '', -- 营业执照相对路径
        legal_person      TEXT NOT NULL DEFAULT '', -- 负责人
        contact_name      TEXT NOT NULL DEFAULT '', -- 联系人
        contact_phone     TEXT NOT NULL DEFAULT '', -- 联系电话
        qualification_path TEXT NOT NULL DEFAULT '', -- 资质资料相对路径
        note              TEXT NOT NULL DEFAULT '', -- 提交备注
        reason            TEXT NOT NULL DEFAULT '', -- 驳回原因
        actor             TEXT NOT NULL,            -- 记录发起角色
        replaced_by       INTEGER REFERENCES carrier_certifications(id) ON DELETE RESTRICT, -- 本记录替代的前序记录
        created_at        TEXT NOT NULL             -- 创建时间，ISO 8601
    ) STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_carrier_cert_account ON carrier_certifications(account_id, id)",
    """
    CREATE TRIGGER IF NOT EXISTS trg_carrier_cert_no_update BEFORE UPDATE ON carrier_certifications
    BEGIN SELECT RAISE(ABORT, 'immutable history'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_carrier_cert_no_delete BEFORE DELETE ON carrier_certifications
    BEGIN SELECT RAISE(ABORT, 'immutable history'); END
    """,
]


def migrate_carrier(conn: sqlite3.Connection) -> None:
    """在已开启的事务内创建物流公司认证表与不可变触发器。"""
    for statement in _CARRIER_CERT_SCHEMA:
        conn.execute(statement)
