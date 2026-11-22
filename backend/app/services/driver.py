"""司机业务：创建、身份绑定、三类状态管理与只读查询。"""

import sqlite3
from datetime import datetime, timezone

from app.core.security import hash_password
from app.exceptions import (
    DriverBindingOrderError,
    DriverNotFoundError,
    PhoneAlreadyRegisteredError,
)
from app.schemas.driver import (
    ChangePasswordIn,
    DriverBindingIn,
    DriverCreateIn,
    DriverIdentityRecord,
    DriverOut,
    DriverSelfOut,
    DriverUpdateIn,
    OnboardingOut,
)

_IDENTITY_COLUMNS = (
    "id, account_id, name, id_number, license_no, license_type, "
    "license_expiry, reason, actor, replaced_by, created_at"
)

_DRIVER_SELECT = """
    SELECT a.id AS account_id, a.phone, a.auth_status, a.account_status,
           dp.name, dp.id_number, dp.license_no, dp.license_type, dp.license_expiry,
           dp.availability, dp.employment, dp.departure_date,
           dp.binding_complete, dp.must_change_password,
           cp.company_name,
           (SELECT v.plate_no FROM vehicles v
            WHERE v.current_driver_id = a.id AND v.carrier_id = dp.carrier_id
            ORDER BY v.id DESC LIMIT 1) AS current_vehicle_plate
    FROM accounts a
    JOIN driver_profiles dp ON dp.account_id = a.id
    LEFT JOIN carrier_profiles cp ON cp.account_id = dp.carrier_id
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _driver_row(conn: sqlite3.Connection, carrier_id: int, account_id: int):
    """取当前公司名下的司机；不存在则抛领域异常。"""
    row = conn.execute(
        _DRIVER_SELECT
        + " WHERE a.role = '司机' AND dp.carrier_id = ? AND a.id = ?",
        (carrier_id, account_id),
    ).fetchone()
    if row is None:
        raise DriverNotFoundError()
    return row


def _self_row(conn: sqlite3.Connection, account_id: int):
    """按账号 id 取司机自身视图所需数据。"""
    return conn.execute(
        _DRIVER_SELECT + " WHERE a.role = '司机' AND a.id = ?", (account_id,)
    ).fetchone()


def _to_out(row) -> DriverOut:
    """将司机行转为出参，并派生派单能力与统计占位。"""
    availability = row["availability"]
    employment = row["employment"]
    account_status = row["account_status"]
    return DriverOut(
        account_id=row["account_id"],
        phone=row["phone"],
        name=row["name"],
        auth_status=row["auth_status"],
        account_status=account_status,
        id_number=row["id_number"],
        license_no=row["license_no"],
        license_type=row["license_type"],
        license_expiry=row["license_expiry"],
        qualification=row["license_type"] or "未填写",
        availability=availability,
        employment=employment,
        departure_date=row["departure_date"],
        binding_complete=bool(row["binding_complete"]),
        must_change_password=bool(row["must_change_password"]),
        # 当前车辆从车辆域投影；任务与历史任务数由派单域接入后投影
        current_vehicle=row["current_vehicle_plate"] or "",
        current_task="",
        historical_task_count=0,
        can_dispatch_new=(
            availability == "可派单"
            and employment == "在职"
            and account_status == "正常使用"
        ),
        can_continue_in_flight=(
            employment == "在职" and account_status == "正常使用"
        ),
    )


def _to_self(row) -> DriverSelfOut:
    """将司机行转为本人视图。"""
    return DriverSelfOut(
        account_id=row["account_id"],
        phone=row["phone"],
        name=row["name"],
        company_name=row["company_name"] or "",
        auth_status=row["auth_status"],
        account_status=row["account_status"],
        availability=row["availability"],
        employment=row["employment"],
        binding_complete=bool(row["binding_complete"]),
        must_change_password=bool(row["must_change_password"]),
    )


def _revoke_sessions(conn: sqlite3.Connection, account_id: int) -> None:
    """撤销该司机全部未失效会话。"""
    conn.execute(
        "UPDATE sessions SET revoked_at = ? WHERE account_id = ? AND revoked_at IS NULL",
        (_now(), account_id),
    )


def _append_identity(
    conn: sqlite3.Connection,
    account_id: int,
    values: dict,
    reason: str,
    actor: str,
) -> None:
    """追加一条身份 / 驾驶资格记录，前序记录由 replaced_by 指回。"""
    prior = conn.execute(
        "SELECT id FROM driver_identity_history WHERE account_id = ? "
        "ORDER BY id DESC LIMIT 1",
        (account_id,),
    ).fetchone()
    conn.execute(
        """INSERT INTO driver_identity_history
           (account_id, name, id_number, license_no, license_type,
            license_expiry, reason, actor, replaced_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            account_id,
            values["name"],
            values["id_number"],
            values["license_no"],
            values["license_type"],
            values["license_expiry"],
            reason,
            actor,
            prior["id"] if prior else None,
            _now(),
        ),
    )


def create_driver(
    conn: sqlite3.Connection, carrier_id: int, payload: DriverCreateIn
) -> DriverOut:
    """创建归属当前物流公司的司机账号，认证状态初始为未提交。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute(
            "SELECT 1 FROM accounts WHERE phone = ?", (payload.phone,)
        ).fetchone():
            raise PhoneAlreadyRegisteredError()
        cursor = conn.execute(
            """INSERT INTO accounts
               (phone, role, account_status, auth_status, password_hash, created_at)
               VALUES (?, '司机', '正常使用', '未提交', ?, ?)""",
            (payload.phone, hash_password(payload.password), _now()),
        )
        account_id = cursor.lastrowid
        conn.execute(
            """INSERT INTO driver_profiles
               (account_id, carrier_id, name, id_number, license_no,
                license_type, license_expiry)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                account_id,
                carrier_id,
                payload.name,
                payload.id_number,
                payload.license_no,
                payload.license_type,
                payload.license_expiry,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _to_out(_driver_row(conn, carrier_id, account_id))


def list_drivers(
    conn: sqlite3.Connection,
    carrier_id: int,
    availability: str | None = None,
    employment: str | None = None,
    account_status: str | None = None,
) -> list[DriverOut]:
    """列出当前公司的司机，可按三类状态筛选。"""
    where = "WHERE a.role = '司机' AND dp.carrier_id = ?"
    params: list = [carrier_id]
    if availability:
        where += " AND dp.availability = ?"
        params.append(availability)
    if employment:
        where += " AND dp.employment = ?"
        params.append(employment)
    if account_status:
        where += " AND a.account_status = ?"
        params.append(account_status)
    rows = conn.execute(
        _DRIVER_SELECT + where + " ORDER BY a.id ASC", params
    ).fetchall()
    return [_to_out(row) for row in rows]


def get_driver(conn: sqlite3.Connection, carrier_id: int, account_id: int) -> DriverOut:
    """读取一名本公司司机的完整资料。"""
    return _to_out(_driver_row(conn, carrier_id, account_id))


def update_driver(
    conn: sqlite3.Connection, carrier_id: int, account_id: int, payload: DriverUpdateIn
) -> DriverOut:
    """修改司机基本资料；身份 / 资格字段变更时追加历史并触发重新审核。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        current = _driver_row(conn, carrier_id, account_id)
        identity_fields = ("id_number", "license_no", "license_type", "license_expiry")
        values = {
            "name": payload.name,
            "id_number": payload.id_number or current["id_number"],
            "license_no": payload.license_no or current["license_no"],
            "license_type": payload.license_type or current["license_type"],
            "license_expiry": payload.license_expiry or current["license_expiry"],
        }
        identity_changed = any(
            getattr(payload, field) is not None
            and getattr(payload, field) != current[field]
            for field in identity_fields
        )
        conn.execute(
            """UPDATE driver_profiles SET name = ?, id_number = ?, license_no = ?,
               license_type = ?, license_expiry = ? WHERE account_id = ?""",
            (
                values["name"],
                values["id_number"],
                values["license_no"],
                values["license_type"],
                values["license_expiry"],
                account_id,
            ),
        )
        if identity_changed:
            _append_identity(conn, account_id, values, "身份资料变更", "物流公司")
            conn.execute(
                "UPDATE accounts SET auth_status = '待审核' WHERE id = ?", (account_id,)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_driver(conn, carrier_id, account_id)


def set_availability(
    conn: sqlite3.Connection, carrier_id: int, account_id: int, availability: str
) -> DriverOut:
    """设置接单可用性；不影响雇佣关系、账号状态或在途任务。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        _driver_row(conn, carrier_id, account_id)
        conn.execute(
            "UPDATE driver_profiles SET availability = ? WHERE account_id = ?",
            (availability, account_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_driver(conn, carrier_id, account_id)


def set_employment(
    conn: sqlite3.Connection, carrier_id: int, account_id: int, employment: str
) -> DriverOut:
    """设置雇佣关系；离职同时禁用账号并撤销会话，保留历史归属。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        _driver_row(conn, carrier_id, account_id)
        if employment == "离职":
            conn.execute(
                """UPDATE driver_profiles SET employment = '离职', departure_date = ?
                   WHERE account_id = ?""",
                (_now(), account_id),
            )
            conn.execute(
                "UPDATE accounts SET account_status = '已禁用' WHERE id = ?",
                (account_id,),
            )
            _revoke_sessions(conn, account_id)
        else:
            conn.execute(
                """UPDATE driver_profiles SET employment = '在职', departure_date = NULL
                   WHERE account_id = ?""",
                (account_id,),
            )
            conn.execute(
                "UPDATE accounts SET account_status = '正常使用' WHERE id = ?",
                (account_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_driver(conn, carrier_id, account_id)


def set_account_status(
    conn: sqlite3.Connection, carrier_id: int, account_id: int, account_status: str
) -> DriverOut:
    """设置账号状态；不改写接单可用性与雇佣关系。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        _driver_row(conn, carrier_id, account_id)
        conn.execute(
            "UPDATE accounts SET account_status = ? WHERE id = ?",
            (account_status, account_id),
        )
        if account_status == "已禁用":
            _revoke_sessions(conn, account_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_driver(conn, carrier_id, account_id)


def identity_history(
    conn: sqlite3.Connection, carrier_id: int, account_id: int
) -> list[DriverIdentityRecord]:
    """读取司机身份历史（只读追加，按时间升序）。"""
    _driver_row(conn, carrier_id, account_id)
    rows = conn.execute(
        f"SELECT {_IDENTITY_COLUMNS} FROM driver_identity_history "
        "WHERE account_id = ? ORDER BY id ASC",
        (account_id,),
    ).fetchall()
    return [DriverIdentityRecord(**dict(row)) for row in rows]


def _blocked_reason(row) -> str:
    """计算司机不可进入工作台的原因；返回空串表示放行。"""
    if row is None:
        return "未绑定物流公司"
    if not row["carrier_id"]:
        return "未绑定物流公司"
    if row["must_change_password"]:
        return "请先修改初始密码"
    if not row["binding_complete"]:
        return "请先完成身份绑定"
    if row["employment"] != "在职":
        return "雇佣关系非在职"
    if row["carrier_account_status"] != "正常使用":
        return "所属物流公司账号异常"
    if row["carrier_auth_status"] != "审核通过":
        return "所属物流公司认证未审核通过"
    return ""


def _onboarding_row(conn: sqlite3.Connection, account_id: int):
    """取身份绑定与所属公司状态，供强制流程与工作台门禁共用。"""
    return conn.execute(
        """SELECT a.auth_status, dp.carrier_id, dp.binding_complete,
                  dp.must_change_password, dp.employment,
                  cp.company_name,
                  ca.account_status AS carrier_account_status,
                  ca.auth_status AS carrier_auth_status
           FROM accounts a
           LEFT JOIN driver_profiles dp ON dp.account_id = a.id
           LEFT JOIN carrier_profiles cp ON cp.account_id = dp.carrier_id
           LEFT JOIN accounts ca ON ca.id = dp.carrier_id
           WHERE a.id = ? AND a.role = '司机'""",
        (account_id,),
    ).fetchone()


def onboarding(conn: sqlite3.Connection, account_id: int) -> OnboardingOut:
    """读取司机首次登录强制流程的当前状态。"""
    row = _onboarding_row(conn, account_id)
    if row is None:
        return OnboardingOut(
            must_change_password=True,
            binding_complete=False,
            company_name="",
            auth_status="未提交",
            blocked_reason="账号不存在",
        )
    return OnboardingOut(
        must_change_password=bool(row["must_change_password"]),
        binding_complete=bool(row["binding_complete"]),
        company_name=row["company_name"] or "",
        auth_status=row["auth_status"],
        blocked_reason=_blocked_reason(row),
    )


def change_password(
    conn: sqlite3.Connection, account_id: int, payload: ChangePasswordIn
) -> None:
    """修改司机口令并清除强制改密标记；不撤销当前会话。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "UPDATE accounts SET password_hash = ? WHERE id = ?",
            (hash_password(payload.new_password), account_id),
        )
        conn.execute(
            "UPDATE driver_profiles SET must_change_password = 0 WHERE account_id = ?",
            (account_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def bind_identity(
    conn: sqlite3.Connection, account_id: int, payload: DriverBindingIn
) -> DriverSelfOut:
    """补全身份与驾驶资格资料完成绑定，并追加一条身份历史。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        state = _onboarding_row(conn, account_id)
        if state is not None and state["must_change_password"]:
            raise DriverBindingOrderError()
        values = {
            "name": payload.name,
            "id_number": payload.id_number,
            "license_no": payload.license_no,
            "license_type": payload.license_type,
            "license_expiry": payload.license_expiry,
        }
        conn.execute(
            """UPDATE driver_profiles SET name = ?, id_number = ?, license_no = ?,
               license_type = ?, license_expiry = ?, binding_complete = 1
               WHERE account_id = ?""",
            (
                values["name"],
                values["id_number"],
                values["license_no"],
                values["license_type"],
                values["license_expiry"],
                account_id,
            ),
        )
        conn.execute(
            "UPDATE accounts SET auth_status = '待审核' WHERE id = ?", (account_id,)
        )
        _append_identity(conn, account_id, values, "首次身份绑定", "司机")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _to_self(_self_row(conn, account_id))


def workspace(conn: sqlite3.Connection, account_id: int) -> DriverSelfOut:
    """读取司机工作台所需的自身资料（门禁由依赖层保证）。"""
    return _to_self(_self_row(conn, account_id))
