"""派单业务：派发规则、时间冲突、司机确认 / 拒绝、未起运重新派单与留痕。"""

import json
import re
import sqlite3
from datetime import datetime, timezone

from app.exceptions import (
    DispatchRuleError,
    DriverNotFoundError,
    OrderNotFoundError,
    TaskNotFoundError,
    TaskStateError,
    VehicleNotFoundError,
)
from app.schemas.dispatch import (
    DispatchCreateIn,
    DispatchHistoryOut,
    DriverPlaceOut,
    DriverTaskOut,
    RedispatchIn,
    TaskOut,
)
from app.schemas.shipper import NotificationOut, OrderOut
from app.services.shipper import ORDER_COLUMNS, to_order_out
from app.services.vehicle import assert_vehicle_assignable

_ACTIVE_STATUSES = ("待司机确认", "待装货", "运输中", "待签收", "待确认完成", "异常")
_REDISPATCHABLE = ("待司机确认", "待装货")

_TASK_SELECT = """
    SELECT t.id, t.task_no, t.order_id, o.order_no, t.carrier_id,
           t.driver_account_id, dp.name AS driver_name, a.phone AS driver_phone,
           t.vehicle_id, v.plate_no AS vehicle_plate, t.status,
           t.planned_load_at, t.planned_deliver_at, t.notes, t.reject_reason,
           t.accepted_at, t.created_at
    FROM transport_tasks t
    JOIN orders o ON o.id = t.order_id
    JOIN accounts a ON a.id = t.driver_account_id
    JOIN driver_profiles dp ON dp.account_id = t.driver_account_id
    JOIN vehicles v ON v.id = t.vehicle_id
"""

_DRIVER_TASK_SELECT = """
    SELECT t.id AS task_id, t.task_no, t.order_id, o.order_no, t.status,
           t.planned_load_at, t.planned_deliver_at, t.notes, t.reject_reason,
           t.accepted_at, t.created_at,
           o.cargo_name, o.cargo_type, o.quantity, o.weight, o.volume, o.packaging,
           o.cargo_photos, o.cargo_remarks,
           o.ship_name, o.ship_contact, o.ship_phone, o.ship_province, o.ship_city,
           o.ship_district, o.ship_detail_address,
           o.recv_name, o.recv_contact, o.recv_phone, o.recv_province, o.recv_city,
           o.recv_district, o.recv_detail_address,
           o.vehicle_type, o.vehicle_length, o.load_requirement, o.cold_chain,
           o.rain_protection, o.enclosed_body, o.special_loading, o.other_services,
           o.transport_remarks,
           v.plate_no AS vehicle_plate, v.vehicle_type AS vehicle_type_actual,
           v.length_m AS vehicle_length_m, v.max_load_kg AS vehicle_max_load_kg,
           cp.company_name AS carrier_company
    FROM transport_tasks t
    JOIN orders o ON o.id = t.order_id
    JOIN vehicles v ON v.id = t.vehicle_id
    LEFT JOIN carrier_profiles cp ON cp.account_id = t.carrier_id
"""

_HISTORY_SELECT = """
    SELECT h.id, h.dispatch_no, h.order_id, h.task_id, h.action,
           h.original_driver_account_id, odn.name AS original_driver_name,
           h.original_vehicle_id, ov.plate_no AS original_vehicle_plate,
           h.new_driver_account_id, ndn.name AS new_driver_name,
           h.new_vehicle_id, nv.plate_no AS new_vehicle_plate,
           h.reason, h.actor, h.replaced_by, h.created_at
    FROM dispatch_history h
    LEFT JOIN driver_profiles odn ON odn.account_id = h.original_driver_account_id
    LEFT JOIN vehicles ov ON ov.id = h.original_vehicle_id
    LEFT JOIN driver_profiles ndn ON ndn.account_id = h.new_driver_account_id
    LEFT JOIN vehicles nv ON nv.id = h.new_vehicle_id
"""

_TYPE_KEYWORDS = (("冷藏", "冷藏车"), ("厢式", "厢式货车"), ("高栏", "高栏货车"), ("平板", "平板货车"))


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str) -> datetime:
    """把 ISO 8601 字符串解析为带时区 datetime，供区间重叠判断。"""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _to_task_out(row) -> TaskOut:
    """把任务行转为物流公司视角出参。"""
    return TaskOut(
        id=row["id"],
        task_no=row["task_no"],
        order_id=row["order_id"],
        order_no=row["order_no"],
        carrier_id=row["carrier_id"],
        driver_account_id=row["driver_account_id"],
        driver_name=row["driver_name"],
        driver_phone=row["driver_phone"],
        vehicle_id=row["vehicle_id"],
        vehicle_plate=row["vehicle_plate"],
        status=row["status"],
        planned_load_at=row["planned_load_at"],
        planned_deliver_at=row["planned_deliver_at"],
        notes=row["notes"],
        reject_reason=row["reject_reason"],
        accepted_at=row["accepted_at"],
        created_at=row["created_at"],
    )


def _to_driver_task_out(row) -> DriverTaskOut:
    """把任务行转为司机出参：只挑选执行所需字段，绝不携带运费报价。"""
    return DriverTaskOut(
        task_id=row["task_id"],
        task_no=row["task_no"],
        order_id=row["order_id"],
        order_no=row["order_no"],
        status=row["status"],
        planned_load_at=row["planned_load_at"],
        planned_deliver_at=row["planned_deliver_at"],
        notes=row["notes"],
        cargo_name=row["cargo_name"],
        cargo_type=row["cargo_type"],
        quantity=row["quantity"],
        weight=row["weight"],
        volume=row["volume"],
        packaging=row["packaging"],
        cargo_photos=json.loads(row["cargo_photos"]),
        cargo_remarks=row["cargo_remarks"],
        shipping=DriverPlaceOut(
            name=row["ship_name"],
            contact=row["ship_contact"],
            phone=row["ship_phone"],
            province=row["ship_province"],
            city=row["ship_city"],
            district=row["ship_district"],
            detail_address=row["ship_detail_address"],
        ),
        receiving=DriverPlaceOut(
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
        vehicle_plate=row["vehicle_plate"],
        vehicle_type_actual=row["vehicle_type_actual"],
        vehicle_length_m=row["vehicle_length_m"],
        vehicle_max_load_kg=row["vehicle_max_load_kg"],
        carrier_company=row["carrier_company"] or "",
        accepted_at=row["accepted_at"],
        reject_reason=row["reject_reason"],
        created_at=row["created_at"],
    )


def _to_history_out(row) -> DispatchHistoryOut:
    """把派单历史行转为出参。"""
    return DispatchHistoryOut(
        id=row["id"],
        dispatch_no=row["dispatch_no"],
        order_id=row["order_id"],
        task_id=row["task_id"],
        action=row["action"],
        original_driver_account_id=row["original_driver_account_id"],
        original_driver_name=row["original_driver_name"] or "",
        original_vehicle_id=row["original_vehicle_id"],
        original_vehicle_plate=row["original_vehicle_plate"] or "",
        new_driver_account_id=row["new_driver_account_id"],
        new_driver_name=row["new_driver_name"] or "",
        new_vehicle_id=row["new_vehicle_id"],
        new_vehicle_plate=row["new_vehicle_plate"] or "",
        reason=row["reason"],
        actor=row["actor"],
        replaced_by=row["replaced_by"],
        created_at=row["created_at"],
    )


def _carrier_task_row(conn: sqlite3.Connection, carrier_id: int, task_id: int):
    """取当前公司名下任务；不存在视为不可见。"""
    row = conn.execute(
        _TASK_SELECT + " WHERE t.carrier_id = ? AND t.id = ?", (carrier_id, task_id)
    ).fetchone()
    if row is None:
        raise TaskNotFoundError()
    return row


def _driver_task_row(conn: sqlite3.Connection, driver_id: int, task_id: int):
    """取派给当前司机的任务；非本人任务视为不可见。"""
    row = conn.execute(
        _DRIVER_TASK_SELECT + " WHERE t.driver_account_id = ? AND t.id = ?",
        (driver_id, task_id),
    ).fetchone()
    if row is None:
        raise TaskNotFoundError()
    return row


def _active_task_for_order(conn: sqlite3.Connection, order_id: int, exclude_id: int | None = None):
    """查询订单上是否已有有效任务。"""
    sql = (
        "SELECT id FROM transport_tasks WHERE order_id = ? AND status IN ("
        + ",".join("?" for _ in _ACTIVE_STATUSES)
        + ")"
    )
    params: list[object] = [order_id, *_ACTIVE_STATUSES]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    return conn.execute(sql, params).fetchone()


def _time_conflict(
    conn: sqlite3.Connection,
    carrier_id: int,
    driver_id: int,
    vehicle_id: int,
    load: str,
    deliver: str,
    exclude_id: int | None = None,
):
    """按计划装货至送达区间判断同司机 / 同车辆的有效任务冲突。"""
    sql = (
        "SELECT id, task_no, planned_load_at, planned_deliver_at FROM transport_tasks "
        "WHERE carrier_id = ? AND status IN ("
        + ",".join("?" for _ in _ACTIVE_STATUSES)
        + ") AND (driver_account_id = ? OR vehicle_id = ?)"
    )
    params: list[object] = [carrier_id, *_ACTIVE_STATUSES, driver_id, vehicle_id]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    rows = conn.execute(sql, params).fetchall()
    new_load, new_deliver = _parse_dt(load), _parse_dt(deliver)
    for row in rows:
        existing_load = _parse_dt(row["planned_load_at"])
        existing_deliver = _parse_dt(row["planned_deliver_at"])
        if existing_load < new_deliver and existing_deliver > new_load:
            return row
    return None


def _validate_driver(conn: sqlite3.Connection, carrier_id: int, driver_id: int):
    """校验司机归属、账号 / 雇佣 / 可用性三类状态与驾驶资格。"""
    row = conn.execute(
        """SELECT a.account_status, dp.employment, dp.availability,
                  dp.binding_complete, dp.license_type
           FROM accounts a JOIN driver_profiles dp ON dp.account_id = a.id
           WHERE a.role = '司机' AND dp.carrier_id = ? AND a.id = ?""",
        (carrier_id, driver_id),
    ).fetchone()
    if row is None:
        raise DriverNotFoundError()
    if row["account_status"] != "正常使用":
        raise DispatchRuleError("司机账号不可用，不可派发新任务")
    if row["employment"] != "在职":
        raise DispatchRuleError("司机已离职，不可派发新任务")
    if row["availability"] != "可派单":
        raise DispatchRuleError(f"司机接单可用性为{row['availability']}，不可派发新任务")
    if not row["binding_complete"] or not (row["license_type"] or "").strip():
        raise DispatchRuleError("司机未完成身份绑定或缺少驾驶资格，不可派单")
    return row


def _validate_vehicle(conn: sqlite3.Connection, carrier_id: int, vehicle_id: int):
    """校验车辆归属与状态，复用车辆域的可派发门禁。"""
    return assert_vehicle_assignable(conn, carrier_id, vehicle_id)


def _vehicle_requirements_reason(order, vehicle) -> str | None:
    """校验车辆满足订单车型 / 载重 / 冷链 / 厢式要求，返回不满足原因。"""
    vehicle_type = vehicle["vehicle_type"]
    wanted = order["vehicle_type"] or ""
    for keyword, mapped in _TYPE_KEYWORDS:
        if keyword in wanted and vehicle_type != mapped:
            return f"车辆类型不满足要求（需{mapped}）"
    if order["cold_chain"] and vehicle_type != "冷藏车":
        return "订单要求冷链运输，需冷藏车"
    if order["enclosed_body"] and vehicle_type not in ("厢式货车", "冷藏车"):
        return "订单要求厢式车身"
    load_text = order["load_requirement"] or ""
    match = re.search(r"(\d+(?:\.\d+)?)", load_text)
    if match:
        amount = float(match.group(1))
        if "吨" in load_text:
            required_kg = amount * 1000
        elif "kg" in load_text or "千克" in load_text:
            required_kg = amount
        else:
            required_kg = 0
        if required_kg and vehicle["max_load_kg"] < required_kg:
            return f"车辆最大载重不满足要求（需 {int(required_kg)} 千克）"
    return None


def _set_occupancy(
    conn: sqlite3.Connection,
    driver_id: int,
    vehicle_id: int,
    *,
    occupy: bool,
) -> None:
    """派单占用或拒绝 / 重新派单释放司机与车辆可用性。"""
    if occupy:
        conn.execute(
            "UPDATE driver_profiles SET availability = '任务占用中' WHERE account_id = ?",
            (driver_id,),
        )
        conn.execute(
            "UPDATE vehicles SET availability = '占用中' WHERE id = ?", (vehicle_id,)
        )
    else:
        conn.execute(
            "UPDATE driver_profiles SET availability = '可派单' "
            "WHERE account_id = ? AND availability = '任务占用中'",
            (driver_id,),
        )
        conn.execute(
            "UPDATE vehicles SET availability = '可用' "
            "WHERE id = ? AND availability = '占用中'",
            (vehicle_id,),
        )


def _append_history(
    conn: sqlite3.Connection,
    *,
    order_id: int,
    task_id: int,
    action: str,
    original_driver_id: int | None,
    original_vehicle_id: int | None,
    new_driver_id: int | None,
    new_vehicle_id: int | None,
    reason: str,
    actor: str,
    now_dt: datetime,
) -> None:
    """追加一条派单历史；只 INSERT，不改动已有记录。"""
    prefix = f"DISP-{now_dt.strftime('%y%m%d')}"
    used = conn.execute(
        "SELECT COUNT(*) FROM dispatch_history WHERE dispatch_no LIKE ?", (f"{prefix}-%",)
    ).fetchone()[0]
    conn.execute(
        """INSERT INTO dispatch_history
           (dispatch_no, order_id, task_id, action,
            original_driver_account_id, original_vehicle_id,
            new_driver_account_id, new_vehicle_id,
            reason, actor, replaced_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
        (
            f"{prefix}-{used + 1:04d}",
            order_id,
            task_id,
            action,
            original_driver_id,
            original_vehicle_id,
            new_driver_id,
            new_vehicle_id,
            reason,
            actor,
            now_dt.isoformat(),
        ),
    )


def _notify(
    conn: sqlite3.Connection,
    recipient_id: int,
    role: str,
    kind: str,
    title: str,
    body: str,
    related_id: int,
    now: str,
) -> None:
    """在通知箱落一条站内通知。"""
    conn.execute(
        """INSERT INTO notifications
           (recipient_id, recipient_role, kind, title, body, related_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (recipient_id, role, kind, title, body, related_id, now),
    )


# --- 物流公司侧 ---


def get_carrier_order(conn: sqlite3.Connection, carrier_id: int, order_id: int) -> OrderOut:
    """物流公司读取自己承接的订单详情。"""
    row = conn.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders WHERE id = ? AND carrier_id = ?",
        (order_id, carrier_id),
    ).fetchone()
    if row is None:
        raise OrderNotFoundError()
    return to_order_out(row)


def list_carrier_orders(
    conn: sqlite3.Connection,
    carrier_id: int,
    status: str | None = None,
    order_no: str | None = None,
    cargo_name: str | None = None,
) -> list[OrderOut]:
    """物流公司列出自己承接的订单，供派单挑选。"""
    clauses = ["carrier_id = ?"]
    params: list[object] = [carrier_id]
    if status:
        clauses.append("status = ?")
        params.append(status)
    if order_no:
        clauses.append("order_no = ?")
        params.append(order_no)
    if cargo_name:
        clauses.append("cargo_name LIKE ?")
        params.append(f"%{cargo_name}%")
    rows = conn.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders WHERE "
        + " AND ".join(clauses)
        + " ORDER BY id DESC",
        params,
    ).fetchall()
    return [to_order_out(row) for row in rows]


def create_dispatch(
    conn: sqlite3.Connection, carrier_id: int, payload: DispatchCreateIn
) -> TaskOut:
    """派单：校验订单、时间冲突、司机与车辆规则后创建运输任务并占用资源。"""
    now_dt = _now_dt()
    now = now_dt.isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        order = conn.execute(
            f"SELECT {ORDER_COLUMNS} FROM orders WHERE id = ?", (payload.order_id,)
        ).fetchone()
        if order is None:
            raise OrderNotFoundError()
        if order["carrier_id"] != carrier_id:
            # 无人承接的订单属规则拒绝；归属其他公司的订单视为不可见
            if order["carrier_id"] is None:
                raise DispatchRuleError("运输订单当前不可派单")
            raise OrderNotFoundError()
        if order["status"] != "已承接":
            raise DispatchRuleError("运输订单当前不可派单")
        if _active_task_for_order(conn, order["id"]) is not None:
            raise DispatchRuleError("运输订单已有运输任务，不可重复派单")
        # 时间冲突先于可用性判断：同一司机 / 车辆在有效任务区间重叠即拒绝
        conflict = _time_conflict(
            conn,
            carrier_id,
            payload.driver_account_id,
            payload.vehicle_id,
            payload.planned_load_at,
            payload.planned_deliver_at,
        )
        if conflict is not None:
            raise DispatchRuleError(
                f"时间冲突：与运输任务 {conflict['task_no']} 的计划装货至送达区间重叠"
            )
        _validate_driver(conn, carrier_id, payload.driver_account_id)
        vehicle = _validate_vehicle(conn, carrier_id, payload.vehicle_id)
        mismatch = _vehicle_requirements_reason(order, vehicle)
        if mismatch:
            raise DispatchRuleError(f"车辆不满足运输要求：{mismatch}")

        prefix = f"TASK-{now_dt.strftime('%y%m%d')}"
        used = conn.execute(
            "SELECT COUNT(*) FROM transport_tasks WHERE task_no LIKE ?", (f"{prefix}-%",)
        ).fetchone()[0]
        task_no = f"{prefix}-{used + 1:04d}"
        cursor = conn.execute(
            """INSERT INTO transport_tasks
               (task_no, order_id, carrier_id, driver_account_id, vehicle_id,
                status, planned_load_at, planned_deliver_at, notes,
                reject_reason, accepted_at, created_at)
               VALUES (?, ?, ?, ?, ?, '待司机确认', ?, ?, ?, '', NULL, ?)""",
            (
                task_no,
                order["id"],
                carrier_id,
                payload.driver_account_id,
                payload.vehicle_id,
                payload.planned_load_at,
                payload.planned_deliver_at,
                payload.notes,
                now,
            ),
        )
        task_id = cursor.lastrowid
        _append_history(
            conn,
            order_id=order["id"],
            task_id=task_id,
            action="派单",
            original_driver_id=None,
            original_vehicle_id=None,
            new_driver_id=payload.driver_account_id,
            new_vehicle_id=payload.vehicle_id,
            reason="",
            actor="物流公司",
            now_dt=now_dt,
        )
        _set_occupancy(conn, payload.driver_account_id, payload.vehicle_id, occupy=True)
        _notify(
            conn,
            payload.driver_account_id,
            "司机",
            "新任务待确认",
            "新运输任务待确认",
            f"运输任务 {task_no} 已派给您，请尽快确认。",
            task_id,
            now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _to_task_out(_carrier_task_row(conn, carrier_id, task_id))


def list_tasks(
    conn: sqlite3.Connection,
    carrier_id: int,
    status: str | None = None,
    order_id: int | None = None,
) -> list[TaskOut]:
    """物流公司列出本公司运输任务。"""
    where = "WHERE t.carrier_id = ?"
    params: list[object] = [carrier_id]
    if status:
        where += " AND t.status = ?"
        params.append(status)
    if order_id:
        where += " AND t.order_id = ?"
        params.append(order_id)
    rows = conn.execute(
        _TASK_SELECT + where + " ORDER BY t.id DESC", params
    ).fetchall()
    return [_to_task_out(row) for row in rows]


def get_task(conn: sqlite3.Connection, carrier_id: int, task_id: int) -> TaskOut:
    """物流公司读取一条运输任务详情。"""
    return _to_task_out(_carrier_task_row(conn, carrier_id, task_id))


def task_dispatch_history(
    conn: sqlite3.Connection, carrier_id: int, task_id: int
) -> list[DispatchHistoryOut]:
    """读取一条任务的派单历史（只读追加，按记录号升序）。"""
    _carrier_task_row(conn, carrier_id, task_id)
    rows = conn.execute(
        _HISTORY_SELECT + " WHERE h.task_id = ? ORDER BY h.id ASC", (task_id,)
    ).fetchall()
    return [_to_history_out(row) for row in rows]


def redispatch(
    conn: sqlite3.Connection, carrier_id: int, task_id: int, payload: RedispatchIn
) -> TaskOut:
    """未起运重新派单：同一任务换司机 / 车辆，追加原新留痕并释放 / 占用资源。"""
    now_dt = _now_dt()
    now = now_dt.isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = _carrier_task_row(conn, carrier_id, task_id)
        if task["status"] not in _REDISPATCHABLE:
            raise TaskStateError("任务已起运或已终结，变更须走运输异常流程")
        order = conn.execute(
            f"SELECT {ORDER_COLUMNS} FROM orders WHERE id = ?", (task["order_id"],)
        ).fetchone()
        conflict = _time_conflict(
            conn,
            carrier_id,
            payload.driver_account_id,
            payload.vehicle_id,
            task["planned_load_at"],
            task["planned_deliver_at"],
            exclude_id=task_id,
        )
        if conflict is not None:
            raise DispatchRuleError(
                f"时间冲突：与运输任务 {conflict['task_no']} 的计划装货至送达区间重叠"
            )
        _validate_driver(conn, carrier_id, payload.driver_account_id)
        vehicle = _validate_vehicle(conn, carrier_id, payload.vehicle_id)
        mismatch = _vehicle_requirements_reason(order, vehicle)
        if mismatch:
            raise DispatchRuleError(f"车辆不满足运输要求：{mismatch}")

        _set_occupancy(conn, task["driver_account_id"], task["vehicle_id"], occupy=False)
        _set_occupancy(conn, payload.driver_account_id, payload.vehicle_id, occupy=True)
        conn.execute(
            """UPDATE transport_tasks SET driver_account_id = ?, vehicle_id = ?,
               status = '待司机确认', accepted_at = NULL, reject_reason = ''
               WHERE id = ? AND carrier_id = ?""",
            (payload.driver_account_id, payload.vehicle_id, task_id, carrier_id),
        )
        _append_history(
            conn,
            order_id=task["order_id"],
            task_id=task_id,
            action="重新派单",
            original_driver_id=task["driver_account_id"],
            original_vehicle_id=task["vehicle_id"],
            new_driver_id=payload.driver_account_id,
            new_vehicle_id=payload.vehicle_id,
            reason=payload.reason,
            actor="物流公司",
            now_dt=now_dt,
        )
        _notify(
            conn,
            payload.driver_account_id,
            "司机",
            "新任务待确认",
            "新运输任务待确认",
            f"运输任务 {task['task_no']} 已重新派给您，请尽快确认。",
            task_id,
            now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _to_task_out(_carrier_task_row(conn, carrier_id, task_id))


def list_notifications(conn: sqlite3.Connection, recipient_id: int) -> list[NotificationOut]:
    """读取当前主体的站内通知。"""
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


# --- 司机侧 ---


def driver_tasks(conn: sqlite3.Connection, driver_id: int) -> list[DriverTaskOut]:
    """司机列出派给自己的运输任务。"""
    rows = conn.execute(
        _DRIVER_TASK_SELECT
        + " WHERE t.driver_account_id = ? ORDER BY t.id DESC",
        (driver_id,),
    ).fetchall()
    return [_to_driver_task_out(row) for row in rows]


def driver_task(conn: sqlite3.Connection, driver_id: int, task_id: int) -> DriverTaskOut:
    """司机读取派给自己的任务详情，不含运费报价。"""
    return _to_driver_task_out(_driver_task_row(conn, driver_id, task_id))


def driver_accept(
    conn: sqlite3.Connection, driver_id: int, task_id: int
) -> DriverTaskOut:
    """司机确认任务：待司机确认 → 待装货，并通知物流公司与货主。"""
    now = _now_dt().isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        summary = conn.execute(
            "SELECT id, carrier_id, order_id, task_no, status FROM transport_tasks "
            "WHERE id = ? AND driver_account_id = ?",
            (task_id, driver_id),
        ).fetchone()
        if summary is None:
            raise TaskNotFoundError()
        if summary["status"] != "待司机确认":
            raise TaskStateError("任务当前状态不可确认")
        conn.execute(
            "UPDATE transport_tasks SET status = '待装货', accepted_at = ? WHERE id = ?",
            (now, task_id),
        )
        shipper = conn.execute(
            "SELECT shipper_id FROM orders WHERE id = ?", (summary["order_id"],)
        ).fetchone()
        body = f"运输任务 {summary['task_no']} 司机已确认，进入待装货。"
        _notify(conn, summary["carrier_id"], "物流公司", "司机已确认任务", "司机已确认任务", body, task_id, now)
        if shipper is not None:
            _notify(conn, shipper["shipper_id"], "货主", "司机已确认任务", "司机已确认任务", body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _to_driver_task_out(_driver_task_row(conn, driver_id, task_id))


def driver_reject(
    conn: sqlite3.Connection, driver_id: int, task_id: int, reason: str
) -> DriverTaskOut:
    """司机拒绝任务：终态已拒绝、订单回到待派单、释放资源并追加历史。"""
    now_dt = _now_dt()
    now = now_dt.isoformat()
    reason = (reason or "").strip()
    if not reason:
        raise DispatchRuleError("拒绝原因必填")
    conn.execute("BEGIN IMMEDIATE")
    try:
        summary = conn.execute(
            """SELECT id, order_id, carrier_id, driver_account_id, vehicle_id,
                      task_no, status FROM transport_tasks
               WHERE id = ? AND driver_account_id = ?""",
            (task_id, driver_id),
        ).fetchone()
        if summary is None:
            raise TaskNotFoundError()
        if summary["status"] != "待司机确认":
            raise TaskStateError("任务当前状态不可拒绝")
        conn.execute(
            "UPDATE transport_tasks SET status = '已拒绝', reject_reason = ? WHERE id = ?",
            (reason, task_id),
        )
        # 待派单语义在当前订单状态机中对应「已承接」，可再次派单
        conn.execute(
            "UPDATE orders SET status = '已承接' WHERE id = ?", (summary["order_id"],)
        )
        _set_occupancy(conn, driver_id, summary["vehicle_id"], occupy=False)
        _append_history(
            conn,
            order_id=summary["order_id"],
            task_id=task_id,
            action="司机拒绝",
            original_driver_id=driver_id,
            original_vehicle_id=summary["vehicle_id"],
            new_driver_id=None,
            new_vehicle_id=None,
            reason=reason,
            actor="司机",
            now_dt=now_dt,
        )
        _notify(
            conn,
            summary["carrier_id"],
            "物流公司",
            "司机拒绝任务",
            "司机拒绝运输任务",
            f"运输任务 {summary['task_no']} 被司机拒绝，原因：{reason}",
            task_id,
            now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _to_driver_task_out(_driver_task_row(conn, driver_id, task_id))
