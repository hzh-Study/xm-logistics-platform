"""评审修复迁移（v17）：追加只读指针与坐标/资质列，仅允许 replaced_by 指针更新。

全部为追加式变更：新增列、重建（等价替换）两个不可变触发器以放行 replaced_by 指针，
不 DROP / 重建任何业务历史表，不改写已发布迁移。见 ADR-0004 与评审修复说明。
"""

import sqlite3

_CARRIER_POINTER_GUARD = """
WHEN NEW.id IS NOT OLD.id
  OR NEW.account_id IS NOT OLD.account_id
  OR NEW.kind IS NOT OLD.kind
  OR NEW.decision IS NOT OLD.decision
  OR NEW.company_name IS NOT OLD.company_name
  OR NEW.license_no IS NOT OLD.license_no
  OR NEW.license_path IS NOT OLD.license_path
  OR NEW.legal_person IS NOT OLD.legal_person
  OR NEW.contact_name IS NOT OLD.contact_name
  OR NEW.contact_phone IS NOT OLD.contact_phone
  OR NEW.qualification_path IS NOT OLD.qualification_path
  OR NEW.note IS NOT OLD.note
  OR NEW.reason IS NOT OLD.reason
  OR NEW.actor IS NOT OLD.actor
  OR NEW.created_at IS NOT OLD.created_at
"""

_SHIPPER_POINTER_GUARD = """
WHEN NEW.id IS NOT OLD.id
  OR NEW.account_id IS NOT OLD.account_id
  OR NEW.cert_type IS NOT OLD.cert_type
  OR NEW.name IS NOT OLD.name
  OR NEW.id_number IS NOT OLD.id_number
  OR NEW.contact_phone IS NOT OLD.contact_phone
  OR NEW.documents IS NOT OLD.documents
  OR NEW.created_at IS NOT OLD.created_at
"""


def _add_column_if_missing(
    conn: sqlite3.Connection, table: str, name: str, definition: str
) -> None:
    """幂等追加列：列已存在时跳过。"""
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def migrate_review_fix(conn: sqlite3.Connection) -> None:
    """在已开启的事务内应用 v17 追加式修复。"""
    # 仓库坐标：发布时固化到订单发货快照，之后不再依赖事后补录
    _add_column_if_missing(conn, "warehouses", "latitude", "latitude REAL")
    _add_column_if_missing(conn, "warehouses", "longitude", "longitude REAL")

    # 特殊货物资质信息：发布时随订单固化
    _add_column_if_missing(
        conn,
        "orders",
        "special_cargo_qualification",
        "special_cargo_qualification TEXT NOT NULL DEFAULT ''",
    )

    # 货主认证提交增加 replaced_by 前向指针：当前记录为 NULL，旧记录指向替代它的新记录
    _add_column_if_missing(
        conn,
        "shipper_certifications",
        "replaced_by",
        "replaced_by INTEGER REFERENCES shipper_certifications(id) ON DELETE RESTRICT",
    )

    # 收窄不可变触发器：仅放行 replaced_by 指针更新，任何实质字段变更仍 ABORT
    conn.execute("DROP TRIGGER IF EXISTS trg_carrier_cert_no_update")
    conn.execute(
        "CREATE TRIGGER trg_carrier_cert_no_update BEFORE UPDATE ON carrier_certifications "
        + _CARRIER_POINTER_GUARD
        + " BEGIN SELECT RAISE(ABORT, 'immutable history'); END"
    )
    conn.execute("DROP TRIGGER IF EXISTS trg_shipper_cert_immutable")
    conn.execute(
        "CREATE TRIGGER trg_shipper_cert_immutable BEFORE UPDATE ON shipper_certifications "
        + _SHIPPER_POINTER_GUARD
        + " BEGIN SELECT RAISE(ABORT, 'immutable history'); END"
    )
