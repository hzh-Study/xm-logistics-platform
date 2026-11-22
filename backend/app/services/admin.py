"""管理员业务：物流公司认证审核与账号状态处置（不改写业务历史）。"""

import sqlite3
from datetime import datetime

from app.exceptions import (
    AccountNotFoundError,
    CarrierNotFoundError,
    DriverNotFoundError,
    OrderNotFoundError,
    TaskNotFoundError,
)
from app.schemas.admin import (
    AccountStatusOut,
    AdminStatsOut,
    AnnouncementIn,
    AnnouncementOut,
    CertItemOut,
    CertReviewOut,
    DriverSummaryOut,
    NoticeIn,
    NoticeOut,
    ShipperSummaryOut,
    UnifiedReviewIn,
    VehicleSummaryOut,
)
from app.schemas.carrier import (
    CarrierSummaryOut,
    CertificationRecordOut,
    ReviewIn,
)
from app.schemas.dispatch import TaskOut
from app.schemas.shipper import OrderOut
from app.services.cert_decision import to_api, to_db
from app.services.dispatch import _TASK_SELECT, _to_task_out
from app.services.shipper import ORDER_COLUMNS, to_order_out

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
    result = []
    for row in rows:
        data = dict(row)
        data["decision"] = to_api(data["decision"])
        result.append(CertificationRecordOut(**data))
    return result


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
            "FROM carrier_certifications WHERE account_id = ? AND replaced_by IS NULL "
            "ORDER BY id DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        if prior is None:
            raise ValueError("尚未提交认证资料")
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """INSERT INTO carrier_certifications
               (account_id, kind, decision, company_name, license_no, license_path,
                legal_person, contact_name, contact_phone, qualification_path,
                note, reason, actor, replaced_by, created_at)
               VALUES (?, '审核', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '管理员', NULL, ?)""",
            (
                account_id,
                to_db(payload.decision),
                prior["company_name"],
                prior["license_no"],
                prior["license_path"],
                prior["legal_person"],
                prior["contact_name"],
                prior["contact_phone"],
                prior["qualification_path"],
                prior["note"],
                payload.reason,
                now,
            ),
        )
        conn.execute(
            "UPDATE carrier_certifications SET replaced_by = ? WHERE id = ?",
            (cursor.lastrowid, prior["id"]),
        )
        # 对外审核结论与账号认证状态同词汇，无需双向 switch
        conn.execute(
            "UPDATE accounts SET auth_status = ? WHERE id = ?",
            (payload.decision, account_id),
        )
        row = conn.execute(
            f"SELECT {_CERT_COLUMNS} FROM carrier_certifications WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    data = dict(row)
    data["decision"] = to_api(data["decision"])
    return CertificationRecordOut(**data)


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
                (datetime.now().isoformat(), account_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    account = _get_carrier(conn, account_id)
    return _summary(account)


# ---- 管理员首页运营统计 ----------------------------------------------------


def stats(conn: sqlite3.Connection) -> AdminStatsOut:
    """汇总各主体数量、订单状态数量与待审核认证数量。"""

    def count(sql: str, params: tuple = ()) -> int:
        return conn.execute(sql, params).fetchone()[0]

    return AdminStatsOut(
        shipper_count=count("SELECT COUNT(*) FROM accounts WHERE role = '货主'"),
        carrier_count=count("SELECT COUNT(*) FROM accounts WHERE role = '物流公司'"),
        driver_count=count("SELECT COUNT(*) FROM accounts WHERE role = '司机'"),
        vehicle_count=count("SELECT COUNT(*) FROM vehicles"),
        orders_pending_accept=count("SELECT COUNT(*) FROM orders WHERE status = '待承接'"),
        orders_in_transit=count("SELECT COUNT(*) FROM orders WHERE status = '运输中'"),
        orders_completed=count("SELECT COUNT(*) FROM orders WHERE status = '已完成'"),
        orders_exception=count("SELECT COUNT(*) FROM orders WHERE status = '异常处理中'"),
        pending_certifications=count(
            "SELECT COUNT(*) FROM accounts WHERE auth_status = '待审核' AND role != '管理员'"
        ),
    )


# ---- 全平台主体查询 --------------------------------------------------------


def list_shippers(
    conn: sqlite3.Connection, company_name: str | None = None, auth_status: str | None = None
) -> list[ShipperSummaryOut]:
    """列出全平台货主，可按企业名称或认证状态筛选。"""
    where = "WHERE accounts.role = '货主'"
    params: list[str] = []
    if company_name:
        where += " AND shipper_profiles.company_name LIKE ? ESCAPE '\\'"
        params.append(f"%{_escape_like(company_name)}%")
    if auth_status:
        where += " AND accounts.auth_status = ?"
        params.append(auth_status)
    rows = conn.execute(
        f"""SELECT accounts.id AS account_id, accounts.phone, accounts.auth_status,
                   accounts.account_status, shipper_profiles.profile_type,
                   shipper_profiles.company_name
            FROM accounts JOIN shipper_profiles
              ON shipper_profiles.account_id = accounts.id
            {where} ORDER BY accounts.id""",
        params,
    ).fetchall()
    return [ShipperSummaryOut(**dict(row)) for row in rows]


def list_drivers(
    conn: sqlite3.Connection, driver_name: str | None = None, auth_status: str | None = None
) -> list[DriverSummaryOut]:
    """列出全平台司机，可按姓名或认证状态筛选。"""
    where = "WHERE accounts.role = '司机'"
    params: list[str] = []
    if driver_name:
        where += " AND driver_profiles.name LIKE ? ESCAPE '\\'"
        params.append(f"%{_escape_like(driver_name)}%")
    if auth_status:
        where += " AND accounts.auth_status = ?"
        params.append(auth_status)
    rows = conn.execute(
        f"""SELECT accounts.id AS account_id, accounts.phone, accounts.auth_status,
                   accounts.account_status, driver_profiles.name AS driver_name,
                   driver_profiles.license_no, driver_profiles.carrier_id,
                   driver_profiles.availability, driver_profiles.employment
            FROM accounts JOIN driver_profiles
              ON driver_profiles.account_id = accounts.id
            {where} ORDER BY accounts.id""",
        params,
    ).fetchall()
    return [DriverSummaryOut(**dict(row)) for row in rows]


def list_vehicles(
    conn: sqlite3.Connection, plate_no: str | None = None, document_review_status: str | None = None
) -> list[VehicleSummaryOut]:
    """列出全平台车辆，可按车牌或证件审核状态筛选。"""
    where = "WHERE 1 = 1"
    params: list[str] = []
    if plate_no:
        where += " AND plate_no LIKE ? ESCAPE '\\'"
        params.append(f"%{_escape_like(plate_no)}%")
    if document_review_status:
        where += " AND document_review_status = ?"
        params.append(document_review_status)
    rows = conn.execute(
        f"""SELECT id, plate_no, carrier_id, vehicle_type, availability, lifecycle,
                   document_status, document_review_status
            FROM vehicles {where} ORDER BY id""",
        params,
    ).fetchall()
    return [VehicleSummaryOut(**dict(row)) for row in rows]


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符，保持字面匹配语义。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ---- 全平台运输订单 / 运输任务查询 ----------------------------------------


def list_orders(
    conn: sqlite3.Connection,
    order_no: str | None = None,
    shipper: str | None = None,
    company: str | None = None,
    status: str | None = None,
    published_from: str | None = None,
    published_to: str | None = None,
) -> list[OrderOut]:
    """按编号/货主/公司/状态/发布时间查询全平台运输订单。"""
    where = "WHERE 1 = 1"
    params: list[str] = []
    if order_no:
        where += " AND order_no LIKE ? ESCAPE '\\'"
        params.append(f"%{_escape_like(order_no)}%")
    if shipper:
        where += (
            " AND shipper_id IN (SELECT account_id FROM shipper_profiles "
            "WHERE company_name LIKE ? ESCAPE '\\' "
            "OR account_id IN (SELECT id FROM accounts WHERE phone LIKE ? ESCAPE '\\'))"
        )
        keyword = f"%{_escape_like(shipper)}%"
        params.extend([keyword, keyword])
    if company:
        where += (
            " AND carrier_id IN (SELECT account_id FROM carrier_profiles "
            "WHERE company_name LIKE ? ESCAPE '\\')"
        )
        params.append(f"%{_escape_like(company)}%")
    if status:
        where += " AND status = ?"
        params.append(status)
    if published_from:
        where += " AND created_at >= ?"
        params.append(published_from)
    if published_to:
        where += " AND created_at <= ?"
        params.append(published_to)
    rows = conn.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders {where} "
        "ORDER BY created_at DESC, id DESC",
        params,
    ).fetchall()
    return [to_order_out(row) for row in rows]


def get_order(conn: sqlite3.Connection, order_id: int) -> OrderOut:
    """读取任意运输订单详情。"""
    row = conn.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        raise OrderNotFoundError()
    return to_order_out(row)


def list_tasks(
    conn: sqlite3.Connection,
    status: str | None = None,
    order_id: int | None = None,
    task_no: str | None = None,
    carrier_id: int | None = None,
    driver_id: int | None = None,
) -> list[TaskOut]:
    """查询全平台运输任务，可按状态/订单/编号/公司/司机筛选。"""
    where = ""
    params: list = []
    clauses: list[str] = []
    if status:
        clauses.append("t.status = ?")
        params.append(status)
    if order_id is not None:
        clauses.append("t.order_id = ?")
        params.append(order_id)
    if task_no:
        clauses.append("t.task_no LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(task_no)}%")
    if carrier_id is not None:
        clauses.append("t.carrier_id = ?")
        params.append(carrier_id)
    if driver_id is not None:
        clauses.append("t.driver_account_id = ?")
        params.append(driver_id)
    if clauses:
        where = " WHERE " + " AND ".join(clauses)
    rows = conn.execute(
        _TASK_SELECT + where + " ORDER BY t.created_at DESC, t.id DESC", params
    ).fetchall()
    return [_to_task_out(row) for row in rows]


def get_task(conn: sqlite3.Connection, task_id: int) -> TaskOut:
    """读取任意运输任务详情。"""
    row = conn.execute(_TASK_SELECT + " WHERE t.id = ?", (task_id,)).fetchone()
    if row is None:
        raise TaskNotFoundError()
    return _to_task_out(row)


# ---- 统一认证审核 ----------------------------------------------------------


def list_certifications(
    conn: sqlite3.Connection, category: str | None = None, status: str | None = None
) -> list[CertItemOut]:
    """聚合五类认证为统一待处理视图；不改写任何原始业务记录。"""
    items: list[CertItemOut] = []
    if category is None or category == "货主":
        for row in conn.execute(
            """SELECT a.id AS account_id, a.phone, a.auth_status, a.account_status,
                      c.id AS cert_id, c.name, c.created_at AS submitted_at,
                      (SELECT r.reason FROM shipper_cert_reviews r
                       WHERE r.certification_id = c.id ORDER BY r.id DESC LIMIT 1) AS reason
               FROM accounts a LEFT JOIN shipper_certifications c
                 ON c.id = (SELECT id FROM shipper_certifications
                            WHERE account_id = a.id AND replaced_by IS NULL)
               WHERE a.role = '货主' ORDER BY a.id"""
        ).fetchall():
            items.append(
                CertItemOut(
                    id=row["cert_id"] or row["account_id"],
                    category="货主",
                    subject_id=row["account_id"],
                    subject_name=row["name"] or row["phone"],
                    auth_status=row["auth_status"],
                    account_status=row["account_status"],
                    submitted_at=row["submitted_at"],
                    reason=row["reason"],
                    detail="货主认证资料",
                )
            )
    if category is None or category == "企业":
        for row in conn.execute(
            """SELECT a.id AS account_id, a.phone, a.auth_status, a.account_status,
                      c.id AS cert_id, c.company_name, c.created_at AS submitted_at,
                      (SELECT r.reason FROM carrier_certifications r
                       WHERE r.id = c.id) AS reason
               FROM accounts a LEFT JOIN carrier_certifications c
                 ON c.id = (SELECT id FROM carrier_certifications
                            WHERE account_id = a.id AND replaced_by IS NULL)
               WHERE a.role = '物流公司' ORDER BY a.id"""
        ).fetchall():
            items.append(
                CertItemOut(
                    id=row["cert_id"] or row["account_id"],
                    category="企业",
                    subject_id=row["account_id"],
                    subject_name=row["company_name"] or row["phone"],
                    auth_status=row["auth_status"],
                    account_status=row["account_status"],
                    submitted_at=row["submitted_at"],
                    reason=row["reason"],
                    detail="企业认证资料",
                )
            )
    if category is None or category == "司机":
        for row in conn.execute(
            """SELECT a.id AS account_id, a.phone, a.auth_status, a.account_status,
                      dp.name, dp.license_no, (SELECT r.reason FROM admin_cert_reviews r
                        WHERE r.category = '司机' AND r.target_id = a.id
                        ORDER BY r.id DESC LIMIT 1) AS reason
               FROM accounts a JOIN driver_profiles dp ON dp.account_id = a.id
               WHERE a.role = '司机' AND dp.binding_complete = 1 ORDER BY a.id"""
        ).fetchall():
            items.append(
                CertItemOut(
                    id=row["account_id"],
                    category="司机",
                    subject_id=row["account_id"],
                    subject_name=row["name"] or row["phone"],
                    auth_status=row["auth_status"],
                    account_status=row["account_status"],
                    submitted_at=None,
                    reason=row["reason"],
                    detail=f"司机身份证明，驾驶证 {row['license_no']}",
                )
            )
    if category is None or category == "驾驶资格":
        for row in conn.execute(
            """SELECT a.id AS account_id, a.phone, a.account_status, dp.name, dp.license_no,
                      dp.qualification_status,
                      (SELECT r.reason FROM admin_cert_reviews r
                       WHERE r.category = '驾驶资格' AND r.target_id = a.id
                       ORDER BY r.id DESC LIMIT 1) AS reason
               FROM accounts a JOIN driver_profiles dp ON dp.account_id = a.id
               WHERE a.role = '司机' AND dp.license_no != '' ORDER BY a.id"""
        ).fetchall():
            items.append(
                CertItemOut(
                    id=row["account_id"],
                    category="驾驶资格",
                    subject_id=row["account_id"],
                    subject_name=row["name"] or row["phone"],
                    auth_status=row["qualification_status"],
                    account_status=row["account_status"],
                    submitted_at=None,
                    reason=row["reason"],
                    detail=f"驾驶资格，准驾车型证件 {row['license_no']}",
                )
            )
    if category is None or category == "车辆证件":
        for row in conn.execute(
            """SELECT v.id, v.plate_no, v.document_review_status,
                      (SELECT r.reason FROM admin_cert_reviews r
                       WHERE r.category = '车辆证件' AND r.target_id = v.id
                       ORDER BY r.id DESC LIMIT 1) AS reason
               FROM vehicles v ORDER BY v.id"""
        ).fetchall():
            items.append(
                CertItemOut(
                    id=row["id"],
                    category="车辆证件",
                    subject_id=row["id"],
                    subject_name=row["plate_no"],
                    auth_status=row["document_review_status"],
                    account_status="",
                    submitted_at=None,
                    reason=row["reason"],
                    detail="车辆证件资料",
                )
            )
    if status:
        items = [item for item in items if item.auth_status == status]
    return items


def _append_admin_review(
    conn: sqlite3.Connection,
    category: str,
    target_id: int,
    decision: str,
    reason: str,
    actor_id: int,
    now: str,
) -> None:
    """追加一条统一审核留痕；原记录不改写。"""
    conn.execute(
        """INSERT INTO admin_cert_reviews
           (category, target_id, decision, reason, actor_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (category, target_id, decision, reason, actor_id, now),
    )


def _review_account_backed(
    conn: sqlite3.Connection,
    category: str,
    target_id: int,
    decision: str,
    reason: str,
    actor_id: int,
    now: str,
) -> None:
    """审核以账号为目标的认证（司机/驾驶资格）：追加留痕并更新状态列。"""
    account = conn.execute(
        "SELECT id, role FROM accounts WHERE id = ? AND role = '司机'", (target_id,)
    ).fetchone()
    if account is None:
        raise DriverNotFoundError()
    conn.execute("BEGIN IMMEDIATE")
    try:
        _append_admin_review(conn, category, target_id, decision, reason, actor_id, now)
        if category == "司机":
            conn.execute(
                "UPDATE accounts SET auth_status = ? WHERE id = ?", (decision, target_id)
            )
        else:
            new_status = "有效" if decision == "审核通过" else "审核不通过"
            conn.execute(
                "UPDATE driver_profiles SET qualification_status = ? WHERE account_id = ?",
                (new_status, target_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _review_vehicle_document(
    conn: sqlite3.Connection,
    target_id: int,
    decision: str,
    reason: str,
    actor_id: int,
    now: str,
) -> None:
    """审核车辆证件：追加留痕并更新证件审核结论列。"""
    vehicle = conn.execute("SELECT id FROM vehicles WHERE id = ?", (target_id,)).fetchone()
    if vehicle is None:
        raise AccountNotFoundError()
    conn.execute("BEGIN IMMEDIATE")
    try:
        _append_admin_review(conn, "车辆证件", target_id, decision, reason, actor_id, now)
        new_status = "有效" if decision == "审核通过" else "驳回"
        conn.execute(
            "UPDATE vehicles SET document_review_status = ? WHERE id = ?",
            (new_status, target_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def unified_review(
    conn: sqlite3.Connection, payload: UnifiedReviewIn, admin_id: int
) -> CertReviewOut:
    """统一入口：复用既有审核服务，其余类别追加留痕；驳回原因由入参模型强制。"""
    reason = (payload.reason or "").strip()
    now = datetime.now().isoformat()
    if payload.category == "货主":
        from app.services.shipper import review_certification as shipper_review

        shipper_review(conn, payload.target_id, payload.decision, reason, admin_id)
    elif payload.category == "企业":
        # 企业认证入参与 GLOSSARY 对齐，库内字面量换算由唯一 helper 完成
        review_certification(
            conn,
            payload.target_id,
            ReviewIn(decision=payload.decision, reason=reason),
        )
    elif payload.category in ("司机", "驾驶资格"):
        _review_account_backed(
            conn, payload.category, payload.target_id, payload.decision, reason, admin_id, now
        )
    else:
        _review_vehicle_document(
            conn, payload.target_id, payload.decision, reason, admin_id, now
        )
    return CertReviewOut(
        category=payload.category,
        target_id=payload.target_id,
        decision=payload.decision,
        reason=reason,
        actor_id=admin_id,
        created_at=now,
    )


# ---- 账号禁用 / 恢复 -------------------------------------------------------


def set_account_status_unified(
    conn: sqlite3.Connection, account_id: int, account_status: str
) -> AccountStatusOut:
    """禁用/恢复任意业务账号；禁用时撤销其全部会话，不改写认证与业务历史。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        account = conn.execute(
            """SELECT id, role FROM accounts
               WHERE id = ? AND role IN ('货主','物流公司','司机')""",
            (account_id,),
        ).fetchone()
        if account is None:
            raise AccountNotFoundError()
        conn.execute(
            "UPDATE accounts SET account_status = ? WHERE id = ?",
            (account_status, account_id),
        )
        if account_status == "已禁用":
            conn.execute(
                "UPDATE sessions SET revoked_at = ? "
                "WHERE account_id = ? AND revoked_at IS NULL",
                (datetime.now().isoformat(), account_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return AccountStatusOut(
        account_id=account_id,
        role=account["role"],
        account_status=account_status,
    )


# ---- 平台公告 / 通知（独立内容通道） --------------------------------------


def publish_announcement(
    conn: sqlite3.Connection, payload: AnnouncementIn, admin_id: int
) -> AnnouncementOut:
    """发布平台公告，仅写入公告表，不产生业务事件或站内通知。"""
    now = datetime.now().isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        cursor = conn.execute(
            """INSERT INTO announcements (title, body, scope, publisher_id, published_at)
               VALUES (?, ?, ?, ?, ?)""",
            (payload.title, payload.body, payload.scope, admin_id, now),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return AnnouncementOut(
        id=cursor.lastrowid,
        title=payload.title,
        body=payload.body,
        scope=payload.scope,
        publisher_id=admin_id,
        published_at=now,
        channel="平台公告",
    )


def list_announcements(conn: sqlite3.Connection) -> list[AnnouncementOut]:
    """列出全部平台公告，按发布时间倒序。"""
    rows = conn.execute(
        """SELECT id, title, body, scope, publisher_id, published_at, channel
           FROM announcements ORDER BY published_at DESC, id DESC"""
    ).fetchall()
    return [AnnouncementOut(**dict(row)) for row in rows]


def publish_notice(
    conn: sqlite3.Connection, payload: NoticeIn, admin_id: int
) -> NoticeOut:
    """发布平台通知，仅写入通知表，不产生业务事件或站内通知。"""
    now = datetime.now().isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        cursor = conn.execute(
            """INSERT INTO notices (title, body, scope, publisher_id, published_at)
               VALUES (?, ?, ?, ?, ?)""",
            (payload.title, payload.body, payload.scope, admin_id, now),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return NoticeOut(
        id=cursor.lastrowid,
        title=payload.title,
        body=payload.body,
        scope=payload.scope,
        publisher_id=admin_id,
        published_at=now,
        channel="平台通知",
    )


def list_notices(conn: sqlite3.Connection) -> list[NoticeOut]:
    """列出全部平台通知，按发布时间倒序。"""
    rows = conn.execute(
        """SELECT id, title, body, scope, publisher_id, published_at, channel
           FROM notices ORDER BY published_at DESC, id DESC"""
    ).fetchall()
    return [NoticeOut(**dict(row)) for row in rows]
