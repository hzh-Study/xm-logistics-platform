"""物流公司业务：注册、企业认证提交与只读查询、业务能力投影。"""

import sqlite3
from datetime import datetime, timezone

from app.core.security import hash_password
from app.exceptions import PhoneAlreadyRegisteredError
from app.schemas.auth import UserOut
from app.schemas.carrier import (
    CapabilitiesOut,
    CertificationRecordOut,
    CertificationSubmitIn,
    CertificationViewOut,
)

_CERT_COLUMNS = (
    "id, account_id, kind, decision, company_name, license_no, license_path, "
    "legal_person, contact_name, contact_phone, qualification_path, note, "
    "reason, actor, replaced_by, created_at"
)


def register_carrier(
    conn: sqlite3.Connection, phone: str, password: str, company_name: str
) -> UserOut:
    """创建物流公司账号及 profile，认证状态初始为未提交。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        exists = conn.execute(
            "SELECT 1 FROM accounts WHERE phone = ?", (phone,)
        ).fetchone()
        if exists is not None:
            raise PhoneAlreadyRegisteredError()
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO accounts
               (phone, role, account_status, auth_status, password_hash, created_at)
               VALUES (?, '物流公司', '正常使用', '未提交', ?, ?)""",
            (phone, hash_password(password), now),
        )
        account_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO carrier_profiles (account_id, company_name, license_no) VALUES (?, ?, '')",
            (account_id, company_name),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return UserOut(
        id=account_id,
        phone=phone,
        role="物流公司",
        account_status="正常使用",
        auth_status="未提交",
    )


def _to_record(row: sqlite3.Row) -> CertificationRecordOut:
    """将认证记录行转为出参模型。"""
    return CertificationRecordOut(**dict(row))


def submit_certification(
    conn: sqlite3.Connection, account_id: int, payload: CertificationSubmitIn
) -> CertificationRecordOut:
    """追加一条企业认证提交记录，并将认证状态置为待审核。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        prior = conn.execute(
            "SELECT id FROM carrier_certifications WHERE account_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO carrier_certifications
               (account_id, kind, decision, company_name, license_no, license_path,
                legal_person, contact_name, contact_phone, qualification_path,
                note, reason, actor, replaced_by, created_at)
               VALUES (?, '提交', '', ?, ?, ?, ?, ?, ?, ?, ?, '', '物流公司', ?, ?)""",
            (
                account_id,
                payload.company_name,
                payload.license_no,
                payload.license_path,
                payload.legal_person,
                payload.contact_name,
                payload.contact_phone,
                payload.qualification_path,
                payload.note,
                prior["id"] if prior else None,
                now,
            ),
        )
        conn.execute(
            "UPDATE accounts SET auth_status = '待审核' WHERE id = ?", (account_id,)
        )
        conn.execute(
            "UPDATE carrier_profiles SET company_name = ? WHERE account_id = ?",
            (payload.company_name, account_id),
        )
        row = conn.execute(
            f"SELECT {_CERT_COLUMNS} FROM carrier_certifications WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _to_record(row)


def certification_view(conn: sqlite3.Connection, account_id: int) -> CertificationViewOut:
    """读取当前认证状态与全部认证记录（历史只读、按 id 升序）。"""
    account = conn.execute(
        "SELECT account_status, auth_status FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    rows = conn.execute(
        f"SELECT {_CERT_COLUMNS} FROM carrier_certifications "
        "WHERE account_id = ? ORDER BY id ASC",
        (account_id,),
    ).fetchall()
    records = [_to_record(row) for row in rows]
    return CertificationViewOut(
        auth_status=account["auth_status"],
        account_status=account["account_status"],
        latest=records[-1] if records else None,
        records=records,
    )


def capabilities(account_status: str, auth_status: str) -> CapabilitiesOut:
    """按账号状态与认证状态计算业务能力；账号状态为阻断权威。"""
    reasons: list[str] = []
    if account_status != "正常使用":
        reasons.append("账号已被禁用")
    if auth_status != "审核通过":
        reasons.append("企业认证未审核通过")
    enabled = not reasons
    return CapabilitiesOut(
        can_accept_orders=enabled,
        can_dispatch=enabled,
        can_manage_drivers=enabled,
        can_manage_vehicles=enabled,
        reasons=reasons,
    )


def company_name_of(conn: sqlite3.Connection, account_id: int) -> str:
    """读取公司名称。"""
    row = conn.execute(
        "SELECT company_name FROM carrier_profiles WHERE account_id = ?", (account_id,)
    ).fetchone()
    return row["company_name"] if row else ""
