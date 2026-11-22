"""货主认证业务：注册、资料提交、审核与发布门禁。"""

import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

from app.core.security import hash_password
from app.exceptions import (
    CertificationNotFoundError,
    CertificationStateError,
    NotPublishableError,
    OrderNotFoundError,
    PhoneTakenError,
    WarehouseNotFoundError,
)
from app.schemas.shipper import (
    AdminCertOut,
    CertificationIn,
    CertificationOut,
    CertificationViewOut,
    NotificationOut,
    OrderOut,
    PublishIn,
    ReceivingSnapshotOut,
    ShippingSnapshotOut,
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


ORDER_COLUMNS = (
    "id, order_no, shipper_id, cargo_name, status, created_at, "
    "cargo_type, quantity, weight, volume, packaging, cargo_photos, cargo_remarks, "
    "ship_source, ship_warehouse_id, ship_name, ship_contact, ship_phone, "
    "ship_province, ship_city, ship_district, ship_detail_address, ship_type, "
    "recv_name, recv_contact, recv_phone, recv_province, recv_city, recv_district, "
    "recv_detail_address, vehicle_type, vehicle_length, load_requirement, "
    "cold_chain, rain_protection, enclosed_body, special_loading, "
    "other_services, transport_remarks, quote_method, quote_amount_cents, "
    "accept_bargain, quote_remarks, carrier_id, accepted_at"
)


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符，保持用户的字面匹配语义。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _cents_to_yuan(cents: int) -> str:
    """库内分转换为 API 边界的元字符串。"""
    return f"{cents // 100}.{cents % 100:02d}"


def to_order_out(row: sqlite3.Row) -> OrderOut:
    """把订单行组装成出参，金额由分转为元，快照独立成对象。"""
    return OrderOut(
        id=row["id"],
        order_no=row["order_no"],
        shipper_id=row["shipper_id"],
        cargo_name=row["cargo_name"],
        status=row["status"],
        carrier_id=row["carrier_id"],
        accepted_at=row["accepted_at"],
        created_at=row["created_at"],
        cargo_type=row["cargo_type"],
        quantity=row["quantity"],
        weight=row["weight"],
        volume=row["volume"],
        packaging=row["packaging"],
        cargo_photos=json.loads(row["cargo_photos"]),
        cargo_remarks=row["cargo_remarks"],
        shipping_snapshot=ShippingSnapshotOut(
            source=row["ship_source"],
            warehouse_id=row["ship_warehouse_id"],
            name=row["ship_name"],
            contact=row["ship_contact"],
            phone=row["ship_phone"],
            province=row["ship_province"],
            city=row["ship_city"],
            district=row["ship_district"],
            detail_address=row["ship_detail_address"],
            type=row["ship_type"],
        ),
        receiving_snapshot=ReceivingSnapshotOut(
            name=row["recv_name"],
            contact=row["recv_contact"],
            phone=row["recv_phone"],
            province=row["recv_province"],
            city=row["recv_city"],
            district=row["recv_district"],
            detail_address=row["recv_detail_address"],
        ),
        vehicle_type=row["vehicle_type"],
        vehicle_length=row["vehicle_length"],
        load_requirement=row["load_requirement"],
        cold_chain=bool(row["cold_chain"]),
        rain_protection=bool(row["rain_protection"]),
        enclosed_body=bool(row["enclosed_body"]),
        special_loading=bool(row["special_loading"]),
        other_services=row["other_services"],
        transport_remarks=row["transport_remarks"],
        quote_method=row["quote_method"],
        quote_amount_yuan=_cents_to_yuan(row["quote_amount_cents"]),
        accept_bargain=bool(row["accept_bargain"]),
        quote_remarks=row["quote_remarks"],
    )


def _get_owned(conn: sqlite3.Connection, shipper_id: int, order_id: int) -> sqlite3.Row:
    """按当前货主读取订单，非本人记录一律视为不存在。"""
    row = conn.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders WHERE id = ? AND shipper_id = ?",
        (order_id, shipper_id),
    ).fetchone()
    if row is None:
        raise OrderNotFoundError()
    return row


def publish_order(
    conn: sqlite3.Connection, account_id: int, data: PublishIn
) -> OrderOut:
    """认证通过后发布订单：固化收发快照，进入待承接并落发布成功通知。"""
    account = conn.execute(
        "SELECT auth_status FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    if account["auth_status"] != "审核通过":
        raise NotPublishableError("认证状态未达审核通过，不能发布运输订单")

    now = datetime.now(timezone.utc)
    prefix = f"ORD-{now.strftime('%y%m%d')}"
    conn.execute("BEGIN IMMEDIATE")
    try:
        if data.warehouse_id is not None:
            warehouse = conn.execute(
                """SELECT name, contact, phone, province, city, district,
                          detail_address, type
                   FROM warehouses
                   WHERE id = ? AND shipper_id = ? AND status = '正常'""",
                (data.warehouse_id, account_id),
            ).fetchone()
            if warehouse is None:
                raise WarehouseNotFoundError()
            ship_source = "仓库"
            ship_warehouse_id: int | None = data.warehouse_id
            ship_name = warehouse["name"]
            ship_contact = warehouse["contact"]
            ship_phone = warehouse["phone"]
            ship_province = warehouse["province"]
            ship_city = warehouse["city"]
            ship_district = warehouse["district"]
            ship_detail_address = warehouse["detail_address"]
            ship_type = warehouse["type"]
        else:
            ship_source = "临时地址"
            ship_warehouse_id = None
            ship_name = data.shipping_name
            ship_contact = data.shipping_contact
            ship_phone = data.shipping_phone
            ship_province = data.shipping_province
            ship_city = data.shipping_city
            ship_district = data.shipping_district
            ship_detail_address = data.shipping_detail_address
            ship_type = "临时地址"

        used = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE order_no LIKE ?", (f"{prefix}-%",)
        ).fetchone()[0]
        order_no = f"{prefix}-{used + 1:04d}"
        created_at = now.isoformat()
        quote_cents = int(Decimal(data.quote_amount_yuan or "0") * 100)
        cursor = conn.execute(
            """INSERT INTO orders
               (order_no, shipper_id, cargo_name, status, created_at,
                cargo_type, quantity, weight, volume, packaging, cargo_photos,
                cargo_remarks, ship_source, ship_warehouse_id, ship_name,
                ship_contact, ship_phone, ship_province, ship_city, ship_district,
                ship_detail_address, ship_type, recv_name, recv_contact,
                recv_phone, recv_province, recv_city, recv_district,
                recv_detail_address, vehicle_type, vehicle_length,
                load_requirement, cold_chain, rain_protection, enclosed_body,
                special_loading, other_services, transport_remarks, quote_method,
                quote_amount_cents, accept_bargain, quote_remarks)
               VALUES (?, ?, ?, '待承接', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                order_no,
                account_id,
                data.cargo_name,
                created_at,
                data.cargo_type,
                data.quantity,
                data.weight,
                data.volume,
                data.packaging,
                json.dumps(data.cargo_photos, ensure_ascii=False),
                data.cargo_remarks,
                ship_source,
                ship_warehouse_id,
                ship_name,
                ship_contact,
                ship_phone,
                ship_province,
                ship_city,
                ship_district,
                ship_detail_address,
                ship_type,
                data.receiving_name,
                data.receiving_contact,
                data.receiving_phone,
                data.receiving_province,
                data.receiving_city,
                data.receiving_district,
                data.receiving_detail_address,
                data.vehicle_type,
                data.vehicle_length,
                data.load_requirement,
                int(data.cold_chain),
                int(data.rain_protection),
                int(data.enclosed_body),
                int(data.special_loading),
                data.other_services,
                data.transport_remarks,
                data.quote_method,
                quote_cents,
                int(data.accept_bargain),
                data.quote_remarks,
            ),
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
        order_id = cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    return to_order_out(_get_owned(conn, account_id, order_id))


def get_order(conn: sqlite3.Connection, shipper_id: int, order_id: int) -> OrderOut:
    """货主读取自己订单的完整详情。"""
    return to_order_out(_get_owned(conn, shipper_id, order_id))


def list_orders(
    conn: sqlite3.Connection,
    shipper_id: int,
    order_no: str | None = None,
    status: str | None = None,
    cargo_name: str | None = None,
    shipping_place: str | None = None,
    receiving_place: str | None = None,
    published_from: str | None = None,
    published_to: str | None = None,
) -> list[OrderOut]:
    """货主按订单号 / 状态 / 时间 / 收发地 / 货物名筛选自己的订单。"""
    clauses = ["shipper_id = ?"]
    params: list[object] = [shipper_id]
    if order_no:
        clauses.append("order_no = ?")
        params.append(order_no)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if cargo_name:
        clauses.append("cargo_name LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(cargo_name)}%")
    if shipping_place:
        clauses.append(
            "(ship_detail_address LIKE ? ESCAPE '\\' OR ship_city LIKE ? ESCAPE '\\')"
        )
        escaped = f"%{_escape_like(shipping_place)}%"
        params.extend([escaped, escaped])
    if receiving_place:
        clauses.append(
            "(recv_detail_address LIKE ? ESCAPE '\\' OR recv_city LIKE ? ESCAPE '\\')"
        )
        escaped = f"%{_escape_like(receiving_place)}%"
        params.extend([escaped, escaped])
    if published_from:
        clauses.append("created_at >= ?")
        params.append(published_from)
    if published_to:
        clauses.append("created_at <= ?")
        params.append(published_to)
    rows = conn.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders WHERE "
        + " AND ".join(clauses)
        + " ORDER BY id DESC",
        params,
    ).fetchall()
    return [to_order_out(row) for row in rows]

