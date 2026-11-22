"""在途异常业务：上报、追加处理记录、换车换司机前后面与订单状态映射。"""

import json
import sqlite3
from datetime import datetime, timezone

from app.exceptions import (
    DriverNotFoundError,
    ExceptionRuleError,
    TaskNotFoundError,
)
from app.schemas.exception import (
    AnomalyIn,
    AnomalyOut,
    ExceptionViewOut,
    HandlingIn,
    HandlingOut,
)
from app.services.vehicle import assert_vehicle_assignable

_PRE_START_STATUSES = ("待装货",)
_IN_TRANSIT_STATUSES = ("运输中", "待签收", "待确认完成", "异常")
_RECOVERY_RESULTS = (
    "继续运输",
    "调整送达时间",
    "更换车辆",
    "更换司机",
    "重新安排运输",
)
_TERMINATE = "终止运输"
_ACTIVE_TASK_STATUSES = ("待司机确认", "待装货", "运输中", "待签收", "待确认完成", "异常")

_TASK_SELECT = """
    SELECT t.id, t.task_no, t.order_id, o.order_no, o.status AS order_status,
           t.carrier_id, o.shipper_id, t.driver_account_id, t.vehicle_id,
           t.status, t.planned_load_at, t.planned_deliver_at
    FROM transport_tasks t JOIN orders o ON o.id = t.order_id
"""

_ANOMALY_SELECT = """
    SELECT a.*, t.task_no
    FROM transport_anomalies a JOIN transport_tasks t ON t.id = a.task_id
"""

_HANDLING_SELECT = """
    SELECT h.*, t.task_no,
           odn.name AS before_driver_name, ndn.name AS after_driver_name,
           ov.plate_no AS before_vehicle_plate, nv.plate_no AS after_vehicle_plate
    FROM exception_handling_records h
    JOIN transport_tasks t ON t.id = h.task_id
    LEFT JOIN driver_profiles odn ON odn.account_id = h.before_driver_account_id
    LEFT JOIN driver_profiles ndn ON ndn.account_id = h.after_driver_account_id
    LEFT JOIN vehicles ov ON ov.id = h.before_vehicle_id
    LEFT JOIN vehicles nv ON nv.id = h.after_vehicle_id
"""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _driver_task(conn: sqlite3.Connection, driver_id: int, task_id: int):
    """取派给当前司机的任务；非本人任务视为不可见。"""
    row = conn.execute(
        _TASK_SELECT + " WHERE t.driver_account_id = ? AND t.id = ?",
        (driver_id, task_id),
    ).fetchone()
    if row is None:
        raise TaskNotFoundError()
    return row


def _carrier_task(conn: sqlite3.Connection, carrier_id: int, task_id: int):
    """取当前公司名下任务；非本公司任务视为不可见。"""
    row = conn.execute(
        _TASK_SELECT + " WHERE t.carrier_id = ? AND t.id = ?",
        (carrier_id, task_id),
    ).fetchone()
    if row is None:
        raise TaskNotFoundError()
    return row


def _shipper_task(conn: sqlite3.Connection, shipper_id: int, order_id: int):
    """取当前货主订单上的任务；非本人订单视为不可见。"""
    row = conn.execute(
        _TASK_SELECT + " WHERE o.shipper_id = ? AND o.id = ? ORDER BY t.id DESC LIMIT 1",
        (shipper_id, order_id),
    ).fetchone()
    if row is None:
        raise TaskNotFoundError()
    return row


def _anomaly_out(row) -> AnomalyOut:
    """把异常行转为出参。"""
    return AnomalyOut(
        id=row["id"],
        anomaly_no=row["anomaly_no"],
        task_id=row["task_id"],
        task_no=row["task_no"],
        order_id=row["order_id"],
        kind=row["kind"],
        detail=row["detail"],
        photos=json.loads(row["photos"]),
        occurred_at=row["occurred_at"],
        started=bool(row["started"]),
        actor=row["actor"],
        created_at=row["created_at"],
    )


def _handling_out(row) -> HandlingOut:
    """把处理记录行转为出参，附带更换前后司机与车辆可读信息。"""
    return HandlingOut(
        id=row["id"],
        handling_no=row["handling_no"],
        anomaly_id=row["anomaly_id"],
        task_id=row["task_id"],
        task_no=row["task_no"],
        result=row["result"],
        detail=row["detail"],
        reason=row["reason"],
        actor=row["actor"],
        before_driver_account_id=row["before_driver_account_id"],
        before_driver_name=row["before_driver_name"] or "",
        before_vehicle_id=row["before_vehicle_id"],
        before_vehicle_plate=row["before_vehicle_plate"] or "",
        after_driver_account_id=row["after_driver_account_id"],
        after_driver_name=row["after_driver_name"] or "",
        after_vehicle_id=row["after_vehicle_id"],
        after_vehicle_plate=row["after_vehicle_plate"] or "",
        before_deliver_at=row["before_deliver_at"],
        after_deliver_at=row["after_deliver_at"],
        order_status=row["order_status"],
        task_status=row["task_status"],
        handled_at=row["handled_at"],
        created_at=row["created_at"],
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


def _set_occupancy(
    conn: sqlite3.Connection,
    driver_id: int,
    vehicle_id: int,
    *,
    occupy: bool,
) -> None:
    """换车换司机时同步司机与车辆可用性：先释放旧资源再占用新资源。"""
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


def _validate_new_driver(conn: sqlite3.Connection, carrier_id: int, driver_id: int):
    """校验新司机归属、账号 / 雇佣 / 可用性状态与驾驶资格。"""
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
        raise ExceptionRuleError("新司机账号不可用，不可更换")
    if row["employment"] != "在职":
        raise ExceptionRuleError("新司机已离职，不可更换")
    if row["availability"] != "可派单":
        raise ExceptionRuleError(f"新司机接单可用性为{row['availability']}，不可更换")
    if not row["binding_complete"] or not (row["license_type"] or "").strip():
        raise ExceptionRuleError("新司机未完成身份绑定或缺少驾驶资格")
    return row


# --- 司机侧 ---


def submit_anomaly(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: AnomalyIn
) -> AnomalyOut:
    """司机上报在途异常：任务转异常、订单转异常处理中，附现场照片。"""
    now_dt = _now_dt()
    now = now_dt.isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = _driver_task(conn, driver_id, task_id)
        if task["status"] not in (*_PRE_START_STATUSES, *_IN_TRANSIT_STATUSES):
            raise ExceptionRuleError("任务当前状态不可上报在途异常")
        if task["status"] in _PRE_START_STATUSES:
            started = 0
        elif task["status"] == "异常":
            prior = conn.execute(
                "SELECT started FROM transport_anomalies WHERE task_id = ? "
                "ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone()
            started = prior["started"] if prior else 1
        else:
            started = 1

        prefix = f"EXC-{now_dt.strftime('%y%m%d')}"
        used = conn.execute(
            "SELECT COUNT(*) FROM transport_anomalies WHERE anomaly_no LIKE ?",
            (f"{prefix}-%",),
        ).fetchone()[0]
        anomaly_no = f"{prefix}-{used + 1:04d}"
        cursor = conn.execute(
            """INSERT INTO transport_anomalies
               (anomaly_no, task_id, order_id, driver_account_id, kind, detail,
                photos, occurred_at, started, actor, reason, replaced_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '司机', '首次上报', NULL, ?)""",
            (
                anomaly_no,
                task_id,
                task["order_id"],
                driver_id,
                payload.kind,
                payload.detail,
                json.dumps(payload.photos, ensure_ascii=False),
                payload.occurred_at,
                started,
                now,
            ),
        )
        anomaly_id = cursor.lastrowid
        conn.execute(
            "UPDATE transport_tasks SET status = '异常' WHERE id = ?", (task_id,)
        )
        conn.execute(
            "UPDATE orders SET status = '异常处理中' WHERE id = ?", (task["order_id"],)
        )
        kind = "在途异常上报"
        body = f"运输任务 {task['task_no']} 上报在途异常（{payload.kind}）：{payload.detail}"
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    row = conn.execute(_ANOMALY_SELECT + " WHERE a.id = ?", (anomaly_id,)).fetchone()
    return _anomaly_out(row)


# --- 物流公司侧 ---


def handle_anomaly(
    conn: sqlite3.Connection,
    carrier_id: int,
    task_id: int,
    anomaly_id: int,
    payload: HandlingIn,
) -> HandlingOut:
    """追加异常处理记录：换车换司机保留前后面，处理结果映射订单状态。"""
    now_dt = _now_dt()
    now = now_dt.isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = _carrier_task(conn, carrier_id, task_id)
        anomaly = conn.execute(
            "SELECT * FROM transport_anomalies WHERE id = ? AND task_id = ?",
            (anomaly_id, task_id),
        ).fetchone()
        if anomaly is None:
            raise TaskNotFoundError()
        if conn.execute(
            "SELECT 1 FROM exception_handling_records WHERE anomaly_id = ?", (anomaly_id,)
        ).fetchone():
            raise ExceptionRuleError("该异常已处理，不可重复追加处理记录")

        before_driver_id = task["driver_account_id"]
        before_vehicle_id = task["vehicle_id"]
        before_deliver_at = task["planned_deliver_at"]
        after_driver_id = before_driver_id
        after_vehicle_id = before_vehicle_id
        after_deliver_at = before_deliver_at

        if payload.result == "更换车辆":
            new_vehicle = assert_vehicle_assignable(
                conn, carrier_id, payload.new_vehicle_id
            )
            after_vehicle_id = new_vehicle["id"]
            _set_occupancy(conn, before_driver_id, before_vehicle_id, occupy=False)
            _set_occupancy(conn, before_driver_id, after_vehicle_id, occupy=True)
            conn.execute(
                "UPDATE transport_tasks SET vehicle_id = ? WHERE id = ? AND carrier_id = ?",
                (after_vehicle_id, task_id, carrier_id),
            )
        elif payload.result == "更换司机":
            _validate_new_driver(conn, carrier_id, payload.new_driver_account_id)
            after_driver_id = payload.new_driver_account_id
            _set_occupancy(conn, before_driver_id, before_vehicle_id, occupy=False)
            _set_occupancy(conn, after_driver_id, before_vehicle_id, occupy=True)
            conn.execute(
                "UPDATE transport_tasks SET driver_account_id = ? "
                "WHERE id = ? AND carrier_id = ?",
                (after_driver_id, task_id, carrier_id),
            )
        elif payload.result == "调整送达时间":
            after_deliver_at = payload.adjusted_deliver_at
            conn.execute(
                "UPDATE transport_tasks SET planned_deliver_at = ? "
                "WHERE id = ? AND carrier_id = ?",
                (after_deliver_at, task_id, carrier_id),
            )

        detail = (payload.detail or "").strip()
        if payload.result == _TERMINATE:
            order_status = "已取消"
            # 任务状态枚举不含「已取消」，任务保持异常的终态；取消以订单状态与处理记录为准
            task_status = "已取消"
            conn.execute(
                "UPDATE orders SET status = '已取消' WHERE id = ?", (task["order_id"],)
            )
        elif anomaly["started"] == 0:
            order_status = "已承接"
            task_status = "待装货"
            conn.execute(
                "UPDATE orders SET status = '已承接' WHERE id = ?", (task["order_id"],)
            )
            conn.execute(
                "UPDATE transport_tasks SET status = '待装货' WHERE id = ?", (task_id,)
            )
        else:
            order_status = "运输中"
            task_status = "运输中"
            conn.execute(
                "UPDATE orders SET status = '运输中' WHERE id = ?", (task["order_id"],)
            )
            conn.execute(
                "UPDATE transport_tasks SET status = '运输中' WHERE id = ?", (task_id,)
            )

        prefix = f"EXCH-{now_dt.strftime('%y%m%d')}"
        used = conn.execute(
            "SELECT COUNT(*) FROM exception_handling_records WHERE handling_no LIKE ?",
            (f"{prefix}-%",),
        ).fetchone()[0]
        handling_no = f"{prefix}-{used + 1:04d}"
        handling_cursor = conn.execute(
            """INSERT INTO exception_handling_records
               (handling_no, anomaly_id, task_id, order_id, result, detail,
                actor_id, actor, before_driver_account_id, before_vehicle_id,
                after_driver_account_id, after_vehicle_id, before_deliver_at,
                after_deliver_at, order_status, task_status, reason, handled_at,
                replaced_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, '物流公司', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
            (
                handling_no,
                anomaly_id,
                task_id,
                task["order_id"],
                payload.result,
                detail,
                carrier_id,
                before_driver_id,
                before_vehicle_id,
                after_driver_id,
                after_vehicle_id,
                before_deliver_at,
                after_deliver_at,
                order_status,
                task_status,
                detail,
                now,
                now,
            ),
        )
        handling_id = handling_cursor.lastrowid
        kind = "异常处理结果"
        notice = f"运输任务 {task['task_no']} 异常处理结果：{payload.result}。" + (
            f"原因：{detail}" if detail else ""
        )
        _notify(conn, task["driver_account_id"], "司机", kind, kind, notice, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, notice, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    row = conn.execute(_HANDLING_SELECT + " WHERE h.id = ?", (handling_id,)).fetchone()
    return _handling_out(row)


def _view(conn: sqlite3.Connection, task) -> ExceptionViewOut:
    """把任务的异常与处理记录汇总为只读视图。"""
    anomalies = [
        _anomaly_out(row)
        for row in conn.execute(
            _ANOMALY_SELECT + " WHERE a.task_id = ? ORDER BY a.id ASC", (task["id"],)
        )
    ]
    handling = [
        _handling_out(row)
        for row in conn.execute(
            _HANDLING_SELECT + " WHERE h.task_id = ? ORDER BY h.id ASC", (task["id"],)
        )
    ]
    return ExceptionViewOut(
        task_id=task["id"],
        task_no=task["task_no"],
        order_id=task["order_id"],
        order_no=task["order_no"],
        anomalies=anomalies,
        handling_records=handling,
    )


def driver_exceptions(
    conn: sqlite3.Connection, driver_id: int, task_id: int
) -> ExceptionViewOut:
    """司机读取本人任务的异常与处理记录。"""
    return _view(conn, _driver_task(conn, driver_id, task_id))


def carrier_exceptions(
    conn: sqlite3.Connection, carrier_id: int, task_id: int
) -> ExceptionViewOut:
    """物流公司读取本公司任务的异常与处理记录。"""
    return _view(conn, _carrier_task(conn, carrier_id, task_id))


def shipper_exceptions(
    conn: sqlite3.Connection, shipper_id: int, order_id: int
) -> ExceptionViewOut:
    """货主只读查看自己订单上的异常与处理记录。"""
    return _view(conn, _shipper_task(conn, shipper_id, order_id))
