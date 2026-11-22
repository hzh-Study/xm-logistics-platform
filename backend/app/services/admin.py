"""管理员业务：物流公司认证审核与账号状态处置（不改写业务历史）。"""

import sqlite3
from datetime import datetime, timezone

from app.exceptions import CarrierNotFoundError
from app.schemas.carrier import (
    CarrierSummaryOut,
    CertificationRecordOut,
    ReviewIn,
)

_CERT_COLUMNS = (
    "id, account_id, kind, decision, company_name, license_no, license_path, "
    "legal_person, contact_name, contact_phone, qualification_path, note, "
    "reason, actor, replaced_by, created_at"
)


def _get_carrier(conn: sqlite3.Connection, account_id: int):
    """取物流公司账号；不存在或非该角色时抛领域异常。"""
    account = conn.execute(
        """SELECT accounts.id, accounts.phone, accounts.auth_status,
                  accounts.account_status, carrier_profiles.company_name,
                  carrier_profiles.license_no
           FROM accounts JOIN carrier_profiles
             ON carrier_profiles.account_id = accounts.id
           WHERE accounts.id = ? AND accounts.role = '物流公司'""",
        (account_id,),
    ).fetchone()
    if account is None:
        raise CarrierNotFoundError()
    return account


def _summary(account) -> CarrierSummaryOut:
    """将物流公司账号行转为摘要出参。"""
    return CarrierSummaryOut(
        account_id=account["id"],
        phone=account["phone"],
        company_name=account["company_name"],
        license_no=account["license_no"],
        account_status=account["account_status"],
        auth_status=account["auth_status"],
    )


def list_carriers(
    conn: sqlite3.Connection, auth_status: str | None = None
) -> list[CarrierSummaryOut]:
    """列出物流公司，可按认证状态筛选。"""
    where = "WHERE accounts.role = '物流公司'"
    params: list[str] = []
    if auth_status:
        where += " AND accounts.auth_status = ?"
        params.append(auth_status)
    rows = conn.execute(
        f"""SELECT accounts.id, accounts.phone, accounts.auth_status,
                   accounts.account_status, carrier_profiles.company_name,
                   carrier_profiles.license_no
            FROM accounts JOIN carrier_profiles
              ON carrier_profiles.account_id = accounts.id
            {where} ORDER BY accounts.id ASC""",
        params,
    ).fetchall()
    return [_summary(row) for row in rows]


def carrier_certifications(
    conn: sqlite3.Connection, account_id: int
) -> list[CertificationRecordOut]:
    """读取指定物流公司的全部认证记录（只读历史）。"""
    _get_carrier(conn, account_id)
    rows = conn.execute(
        f"SELECT {_CERT_COLUMNS} FROM carrier_certifications "
        "WHERE account_id = ? ORDER BY id ASC",
        (account_id,),
    ).fetchall()
    return [CertificationRecordOut(**dict(row)) for row in rows]


def review_certification(
    conn: sqlite3.Connection, account_id: int, payload: ReviewIn
) -> CertificationRecordOut:
    """追加一条审核记录并更新认证状态；原提交记录不改写。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        _get_carrier(conn, account_id)
        prior = conn.execute(
            "SELECT id, company_name, license_no, license_path, legal_person, "
            "contact_name, contact_phone, qualification_path, note "
            "FROM carrier_certifications WHERE account_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        if prior is None:
            raise ValueError("尚未提交认证资料")
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO carrier_certifications
               (account_id, kind, decision, company_name, license_no, license_path,
                legal_person, contact_name, contact_phone, qualification_path,
                note, reason, actor, replaced_by, created_at)
               VALUES (?, '审核', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '管理员', ?, ?)""",
            (
                account_id,
                payload.decision,
                prior["company_name"],
                prior["license_no"],
                prior["license_path"],
                prior["legal_person"],
                prior["contact_name"],
                prior["contact_phone"],
                prior["qualification_path"],
                prior["note"],
                payload.reason,
                prior["id"],
                now,
            ),
        )
        new_status = "审核通过" if payload.decision == "通过" else "审核不通过"
        conn.execute(
            "UPDATE accounts SET auth_status = ? WHERE id = ?", (new_status, account_id)
        )
        row = conn.execute(
            f"SELECT {_CERT_COLUMNS} FROM carrier_certifications WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return CertificationRecordOut(**dict(row))


def set_account_status(
    conn: sqlite3.Connection, account_id: int, account_status: str
) -> CarrierSummaryOut:
    """设置物流公司账号状态；禁用时撤销其全部会话，认证记录不变。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        account = _get_carrier(conn, account_id)
        conn.execute(
            "UPDATE accounts SET account_status = ? WHERE id = ?",
            (account_status, account_id),
        )
        if account_status == "已禁用":
            conn.execute(
                "UPDATE sessions SET revoked_at = ? "
                "WHERE account_id = ? AND revoked_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), account_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    account = _get_carrier(conn, account_id)
    return _summary(account)
