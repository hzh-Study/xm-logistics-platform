"""货主认证业务：注册、资料提交、审核与发布门禁。"""

import json
import sqlite3
from datetime import datetime, timezone

from app.core.security import hash_password
from app.exceptions import (
    CertificationNotFoundError,
    CertificationStateError,
    NotPublishableError,
    PhoneTakenError,
)
from app.schemas.shipper import (
    AdminCertOut,
    CertificationIn,
    CertificationOut,
    CertificationViewOut,
    NotificationOut,
    OrderOut,
)

_SUBMISSION_COLUMNS = (
    "id, cert_type, name, id_number, contact_phone, documents, created_at"
)


def register_shipper(conn: sqlite3.Connection, phone: str, password: str) -> None:
    """创建货主账号与 profile，初始认证状态为未提交。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        exists = conn.execute(
            "SELECT 1 FROM accounts WHERE phone = ?", (phone,)
        ).fetchone()
        if exists:
            raise PhoneTakenError()
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO accounts
               (phone, role, account_status, auth_status, password_hash, created_at)
               VALUES (?, '货主', '正常使用', '未提交', ?, ?)""",
            (phone, hash_password(password), now),
        )
        conn.execute(
            "INSERT INTO shipper_profiles (account_id) VALUES (?)",
            (cursor.lastrowid,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_certification_view(
    conn: sqlite3.Connection, account_id: int, auth_status: str
) -> CertificationViewOut:
    """读取当前认证状态、当前提交与全部提交历史。"""
    submissions = conn.execute(
        f"SELECT {_SUBMISSION_COLUMNS} FROM shipper_certifications "
        "WHERE account_id = ? ORDER BY id DESC",
        (account_id,),
    ).fetchall()
    history: list[CertificationOut] = []
    for sub in submissions:
        review = conn.execute(
            """SELECT decision, reason, actor_id, created_at
               FROM shipper_cert_reviews WHERE certification_id = ?
               ORDER BY id DESC LIMIT 1""",
            (sub["id"],),
        ).fetchone()
        status = review["decision"] if review else "待审核"
        history.append(
            CertificationOut(
                id=sub["id"],
                cert_type=sub["cert_type"],
                name=sub["name"],
                id_number=sub["id_number"],
                contact_phone=sub["contact_phone"],
                documents=json.loads(sub["documents"]),
                status=status,
                rejection_reason=(
                    review["reason"]
                    if review and review["decision"] == "审核不通过"
                    else None
                ),
                reviewer_id=review["actor_id"] if review else None,
                reviewed_at=review["created_at"] if review else None,
                submitted_at=sub["created_at"],
            )
        )
    return CertificationViewOut(
        auth_status=auth_status,
        current=history[0] if history else None,
        history=history,
    )


def submit_certification(
    conn: sqlite3.Connection, account_id: int, data: CertificationIn
) -> CertificationOut:
    """追加一条认证提交并把认证状态置为待审核。"""
    current = conn.execute(
        "SELECT auth_status FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    if current["auth_status"] in ("待审核", "审核通过"):
        raise CertificationStateError("当前认证状态不允许提交资料")
    conn.execute("BEGIN IMMEDIATE")
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO shipper_certifications
               (account_id, cert_type, name, id_number, contact_phone, documents, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                account_id,
                data.cert_type,
                data.name,
                data.id_number,
                data.contact_phone,
                json.dumps(data.documents, ensure_ascii=False),
                now,
            ),
        )
        conn.execute(
            "UPDATE accounts SET auth_status = '待审核' WHERE id = ?", (account_id,)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_certification_view(conn, account_id, "待审核").current


def list_admin_certifications(conn: sqlite3.Connection) -> list[AdminCertOut]:
    """管理员列出全部货主（含未提交）及其最新认证提交与审核结果。"""
    rows = conn.execute(
        """SELECT a.id AS account_id, a.phone, a.auth_status, a.account_status,
                  c.id AS certification_id, c.cert_type, c.name, c.id_number,
                  c.contact_phone, c.documents, c.created_at AS submitted_at
           FROM accounts a
           LEFT JOIN shipper_certifications c ON c.id = (
               SELECT id FROM shipper_certifications
               WHERE account_id = a.id ORDER BY id DESC LIMIT 1
           )
           WHERE a.role = '货主' ORDER BY a.id"""
    ).fetchall()
    result: list[AdminCertOut] = []
    for row in rows:
        review = None
        if row["certification_id"] is not None:
            review = conn.execute(
                """SELECT decision, reason, created_at FROM shipper_cert_reviews
                   WHERE certification_id = ? ORDER BY id DESC LIMIT 1""",
                (row["certification_id"],),
            ).fetchone()
        result.append(
            AdminCertOut(
                account_id=row["account_id"],
                phone=row["phone"],
                auth_status=row["auth_status"],
                account_status=row["account_status"],
                certification_id=row["certification_id"],
                cert_type=row["cert_type"],
                name=row["name"],
                id_number=row["id_number"],
                contact_phone=row["contact_phone"],
                documents=json.loads(row["documents"]) if row["documents"] else [],
                status=(
                    review["decision"]
                    if review
                    else ("待审核" if row["certification_id"] is not None else None)
                ),
                rejection_reason=(
                    review["reason"]
                    if review and review["decision"] == "审核不通过"
                    else None
                ),
                submitted_at=row["submitted_at"],
                reviewed_at=review["created_at"] if review else None,
            )
        )
    return result


def _notification_kind_and_body(decision: str, reason: str) -> tuple[str, str]:
    """按审核结论生成通知类型与正文。"""
    if decision == "审核通过":
        return "认证审核通过", "您的货主认证资料已审核通过。"
    return "认证驳回", f"您的货主认证资料未通过审核，原因：{reason}"


def review_certification(
    conn: sqlite3.Connection,
    certification_id: int,
    decision: str,
    reason: str,
    actor_id: int,
) -> AdminCertOut:
    """追加审核记录、更新认证状态并给货主落一条通知。"""
    cert = conn.execute(
        "SELECT account_id FROM shipper_certifications WHERE id = ?",
        (certification_id,),
    ).fetchone()
    if cert is None:
        raise CertificationNotFoundError()
    latest = conn.execute(
        """SELECT MAX(id) FROM shipper_certifications WHERE account_id = ?""",
        (cert["account_id"],),
    ).fetchone()[0]
    if latest != certification_id:
        raise CertificationStateError("只能审核最新一次认证提交")
    reviewed = conn.execute(
        "SELECT 1 FROM shipper_cert_reviews WHERE certification_id = ?",
        (certification_id,),
    ).fetchone()
    if reviewed:
        raise CertificationStateError("该认证提交已审核")
    reason = reason.strip() if reason else ""
    if decision == "审核不通过" and not reason:
        raise CertificationStateError("驳回原因必填")

    now = datetime.now(timezone.utc).isoformat()
    kind, body = _notification_kind_and_body(decision, reason)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """INSERT INTO shipper_cert_reviews
               (certification_id, decision, reason, actor_id, created_at, replaced_by)
               VALUES (?, ?, ?, ?, ?, NULL)""",
            (certification_id, decision, reason, actor_id, now),
        )
        conn.execute(
            "UPDATE accounts SET auth_status = ? WHERE id = ?",
            (decision, cert["account_id"]),
        )
        conn.execute(
            """INSERT INTO notifications
               (recipient_id, recipient_role, kind, title, body, related_id, created_at)
               VALUES (?, '货主', ?, ?, ?, ?, ?)""",
            (cert["account_id"], kind, "货主认证审核结果", body, certification_id, now),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return next(
        item
        for item in list_admin_certifications(conn)
        if item.certification_id == certification_id
    )


def list_notifications(
    conn: sqlite3.Connection, recipient_id: int
) -> list[NotificationOut]:
    """读取当前货主的站内通知。"""
    rows = conn.execute(
        """SELECT id, kind, title, body, related_id, created_at
           FROM notifications WHERE recipient_id = ? ORDER BY id DESC""",
        (recipient_id,),
    ).fetchall()
    return [
        NotificationOut(
            id=row["id"],
            kind=row["kind"],
            title=row["title"],
            body=row["body"],
            related_id=row["related_id"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def publish_order(
    conn: sqlite3.Connection, account_id: int, cargo_name: str
) -> OrderOut:
    """仅当认证已通过时创建运输订单，并落一条发布成功通知。"""
    account = conn.execute(
        "SELECT auth_status FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    if account["auth_status"] != "审核通过":
        raise NotPublishableError("认证状态未达审核通过，不能发布运输订单")

    now = datetime.now(timezone.utc)
    prefix = f"ORD-{now.strftime('%y%m%d')}"
    conn.execute("BEGIN IMMEDIATE")
    try:
        used = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE order_no LIKE ?", (f"{prefix}-%",)
        ).fetchone()[0]
        order_no = f"{prefix}-{used + 1:04d}"
        created_at = now.isoformat()
        cursor = conn.execute(
            """INSERT INTO orders (order_no, shipper_id, cargo_name, status, created_at)
               VALUES (?, ?, ?, '待承接', ?)""",
            (order_no, account_id, cargo_name, created_at),
        )
        conn.execute(
            """INSERT INTO notifications
               (recipient_id, recipient_role, kind, title, body, related_id, created_at)
               VALUES (?, '货主', '订单发布成功', '运输订单发布成功', ?, ?, ?)""",
            (
                account_id,
                f"运输订单 {order_no} 发布成功，进入待承接。",
                cursor.lastrowid,
                created_at,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return OrderOut(
        id=cursor.lastrowid,
        order_no=order_no,
        shipper_id=account_id,
        cargo_name=cargo_name,
        status="待承接",
        created_at=created_at,
    )


def list_orders(conn: sqlite3.Connection, account_id: int) -> list[OrderOut]:
    """货主读取自己的运输订单。"""
    rows = conn.execute(
        """SELECT id, order_no, shipper_id, cargo_name, status, created_at
           FROM orders WHERE shipper_id = ? ORDER BY id DESC""",
        (account_id,),
    ).fetchall()
    return [
        OrderOut(
            id=row["id"],
            order_no=row["order_no"],
            shipper_id=row["shipper_id"],
            cargo_name=row["cargo_name"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]

