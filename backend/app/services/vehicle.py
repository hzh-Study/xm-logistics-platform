"""车辆业务：登记、两个独立状态维度、公司车辆分配与可派发门禁。"""

import sqlite3
from datetime import datetime, timezone

from app.exceptions import (
    DriverNotFoundError,
    VehicleNotAssignableError,
    VehicleNotFoundError,
    VehicleOwnerDriverError,
    VehiclePlateTakenError,
)
from app.schemas.vehicle import (
    VehicleCreateIn,
    Lifecycle,
    DocumentStatus,
    Availability,
    VehicleOut,
)

_VEHICLE_SELECT = """
    SELECT v.id, v.plate_no, v.vehicle_type, v.length_m, v.max_load_kg,
           v.owner_type, v.owner_driver_id, v.current_driver_id,
           v.availability, v.lifecycle, v.document_status, v.created_at,
           cp.company_name,
           ownerdp.name AS owner_driver_name,
           curdp.name AS current_driver_name
    FROM vehicles v
    LEFT JOIN carrier_profiles cp ON cp.account_id = v.carrier_id
    LEFT JOIN driver_profiles ownerdp ON ownerdp.account_id = v.owner_driver_id
    LEFT JOIN driver_profiles curdp ON curdp.account_id = v.current_driver_id
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vehicle_row(conn: sqlite3.Connection, carrier_id: int, vehicle_id: int):
    """取当前公司名下车辆；不存在则抛领域异常。"""
    row = conn.execute(
        _VEHICLE_SELECT + " WHERE v.carrier_id = ? AND v.id = ?",
        (carrier_id, vehicle_id),
    ).fetchone()
    if row is None:
        raise VehicleNotFoundError()
    return row


def is_vehicle_assignable(row) -> bool:
    """判断车辆是否可分配给司机或派发新任务（派单域可复用此门禁）。"""
    return row["availability"] == "可用" and row["lifecycle"] == "在册"


def _assignable_reason(row) -> str | None:
    """返回车辆不可分配的具体原因；可分配时返回空。"""
    if row["lifecycle"] == "维修中":
        return "车辆维修中，不可分配或派发新任务"
    if row["lifecycle"] == "已停用":
        return "车辆已停用，不可分配或派发新任务"
    if row["availability"] == "暂停使用":
        return "车辆暂停使用，不可分配或派发新任务"
    if row["availability"] == "占用中":
        return "车辆占用中，不可分配或派发新任务"
    return None


def assert_vehicle_assignable(conn: sqlite3.Connection, carrier_id: int, vehicle_id: int):
    """派单域可调用：校验车辆归属且状态可用，返回车辆行。"""
    row = _vehicle_row(conn, carrier_id, vehicle_id)
    reason = _assignable_reason(row)
    if reason:
        raise VehicleNotAssignableError(reason)
    return row


def _to_out(row) -> VehicleOut:
    """将车辆行转为出参，并派生实际所有者、当前司机与可分配标记。"""
    if row["owner_type"] == "公司":
        actual_owner = row["company_name"] or ""
    else:
        actual_owner = row["owner_driver_name"] or ""
    return VehicleOut(
        id=row["id"],
        plate_no=row["plate_no"],
        vehicle_type=row["vehicle_type"],
        length_m=row["length_m"],
        max_load_kg=row["max_load_kg"],
        owner_type=row["owner_type"],
        actual_owner=actual_owner,
        owner_driver_id=row["owner_driver_id"],
        current_driver_id=row["current_driver_id"],
        current_driver=row["current_driver_name"] or "",
        availability=row["availability"],
        lifecycle=row["lifecycle"],
        document_status=row["document_status"],
        assignable=is_vehicle_assignable(row),
        created_at=row["created_at"],
    )


def get_vehicle(conn: sqlite3.Connection, carrier_id: int, vehicle_id: int) -> VehicleOut:
    """读取当前公司名下车辆详情。"""
    return _to_out(_vehicle_row(conn, carrier_id, vehicle_id))


def create_vehicle(
    conn: sqlite3.Connection, carrier_id: int, payload: VehicleCreateIn
) -> VehicleOut:
    """登记车辆；个人车辆默认关联所属司机并纳入公司管理。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute(
            "SELECT 1 FROM vehicles WHERE plate_no = ?", (payload.plate_no,)
        ).fetchone():
            raise VehiclePlateTakenError()
        current_driver_id = None
        if payload.owner_type == "司机":
            if payload.owner_driver_id is None:
                raise VehicleOwnerDriverError("个人车辆必须关联所属司机")
            owned = conn.execute(
                "SELECT 1 FROM driver_profiles WHERE account_id = ? AND carrier_id = ?",
                (payload.owner_driver_id, carrier_id),
            ).fetchone()
            if owned is None:
                raise VehicleOwnerDriverError("个人车辆必须关联本公司司机")
            current_driver_id = payload.owner_driver_id
        now = _now()
        cursor = conn.execute(
            """INSERT INTO vehicles
               (plate_no, carrier_id, vehicle_type, length_m, max_load_kg,
                owner_type, owner_driver_id, current_driver_id, availability,
                lifecycle, document_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, '可用', '在册', ?, ?, ?)""",
            (
                payload.plate_no,
                carrier_id,
                payload.vehicle_type,
                payload.length_m,
                payload.max_load_kg,
                payload.owner_type,
                payload.owner_driver_id if payload.owner_type == "司机" else None,
                current_driver_id,
                payload.document_status,
                now,
                now,
            ),
        )
        vehicle_id = cursor.lastrowid
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_vehicle(conn, carrier_id, vehicle_id)


def list_vehicles(
    conn: sqlite3.Connection,
    carrier_id: int,
    availability: Availability | None = None,
    lifecycle: Lifecycle | None = None,
    owner_type: str | None = None,
    assignable: bool = False,
) -> list[VehicleOut]:
    """列出当前公司车辆，可按两个独立状态、所有者与可分配性筛选。"""
    where = "WHERE v.carrier_id = ?"
    params: list = [carrier_id]
    if availability:
        where += " AND v.availability = ?"
        params.append(availability)
    if lifecycle:
        where += " AND v.lifecycle = ?"
        params.append(lifecycle)
    if owner_type:
        where += " AND v.owner_type = ?"
        params.append(owner_type)
    if assignable:
        where += " AND v.availability = '可用' AND v.lifecycle = '在册'"
    rows = conn.execute(
        _VEHICLE_SELECT + where + " ORDER BY v.id ASC", params
    ).fetchall()
    return [_to_out(row) for row in rows]


def assign_vehicle(
    conn: sqlite3.Connection, carrier_id: int, vehicle_id: int, driver_account_id: int
) -> VehicleOut:
    """把公司名下可用车辆分配给本公司司机；不改动两个状态维度。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _vehicle_row(conn, carrier_id, vehicle_id)
        if row["owner_type"] != "公司":
            raise VehicleNotAssignableError("个人车辆已默认关联所属司机，不可再分配")
        reason = _assignable_reason(row)
        if reason:
            raise VehicleNotAssignableError(reason)
        owned = conn.execute(
            "SELECT 1 FROM driver_profiles WHERE account_id = ? AND carrier_id = ?",
            (driver_account_id, carrier_id),
        ).fetchone()
        if owned is None:
            raise DriverNotFoundError()
        conn.execute(
            "UPDATE vehicles SET current_driver_id = ?, updated_at = ? "
            "WHERE id = ? AND carrier_id = ?",
            (driver_account_id, _now(), vehicle_id, carrier_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_vehicle(conn, carrier_id, vehicle_id)


def set_availability(
    conn: sqlite3.Connection, carrier_id: int, vehicle_id: int, availability: Availability
) -> VehicleOut:
    """设置可用性；不影响生命周期。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        _vehicle_row(conn, carrier_id, vehicle_id)
        conn.execute(
            "UPDATE vehicles SET availability = ?, updated_at = ? WHERE id = ? AND carrier_id = ?",
            (availability, _now(), vehicle_id, carrier_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_vehicle(conn, carrier_id, vehicle_id)


def set_lifecycle(
    conn: sqlite3.Connection, carrier_id: int, vehicle_id: int, lifecycle: Lifecycle
) -> VehicleOut:
    """设置生命周期；不影响可用性。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        _vehicle_row(conn, carrier_id, vehicle_id)
        conn.execute(
            "UPDATE vehicles SET lifecycle = ?, updated_at = ? WHERE id = ? AND carrier_id = ?",
            (lifecycle, _now(), vehicle_id, carrier_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_vehicle(conn, carrier_id, vehicle_id)


def set_document_status(
    conn: sqlite3.Connection, carrier_id: int, vehicle_id: int, document_status: DocumentStatus
) -> VehicleOut:
    """设置证件状态。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        _vehicle_row(conn, carrier_id, vehicle_id)
        conn.execute(
            "UPDATE vehicles SET document_status = ?, updated_at = ? "
            "WHERE id = ? AND carrier_id = ?",
            (document_status, _now(), vehicle_id, carrier_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_vehicle(conn, carrier_id, vehicle_id)
