"""签收业务：收货地打卡、卸货凭证、签收资料、公司确认与完成通知。"""

import json
import sqlite3
from datetime import datetime

from app.exceptions import (
    OrderNotFoundError,
    SignoffRuleError,
    TaskNotFoundError,
    TaskStateError,
)
from app.schemas.checkin import TaskProgressOut
from app.schemas.signoff import (
    ArrivalCheckinIn,
    ArrivalCheckinOut,
    ArrivalNoteIn,
    ArrivalNoteOut,
    ReceivingCoordinateIn,
    ReceivingCoordinateOut,
    SignoffConfirmIn,
    SignoffIn,
    UnloadingAnomalyIn,
    UnloadingAnomalyOut,
    UnloadingPhotosIn,
    UnloadingPhotosOut,
)
from app.services import checkin as checkin_service
from app.services.notify import notify as _notify

_UNLOADING_PHASES = ("卸货前", "卸货中", "卸货完成")


def _now() -> str:
    return datetime.now().isoformat()


def _latest_arrival_checkin(conn: sqlite3.Connection, task_id: int):
    """取任务当前有效的收货地打卡（只读追加，replaced_by 为空）。"""
    return conn.execute(
        """SELECT id, task_id, order_id, driver_account_id, latitude, longitude,
                  arrived_at, photos, notes, position_status, distance_m,
                  reason, actor, replaced_by, created_at
           FROM arrival_checkins
           WHERE task_id = ? AND replaced_by IS NULL ORDER BY id DESC LIMIT 1""",
        (task_id,),
    ).fetchone()


def _voucher_no(conn: sqlite3.Connection, now: str) -> str:
    """按天生成签收凭证号，SIGN-YYMMDD-0001，单事务内不重号。"""
    prefix = f"SIGN-{datetime.fromisoformat(now).strftime('%y%m%d')}"
    used = conn.execute(
        "SELECT COUNT(*) FROM signoff_vouchers WHERE voucher_no LIKE ?", (f"{prefix}-%",)
    ).fetchone()[0]
    return f"{prefix}-{used + 1:04d}"


# --- 货主侧：补录收货快照坐标 ---


def set_receiving_coordinate(
    conn: sqlite3.Connection, shipper_id: int, order_id: int, payload: ReceivingCoordinateIn
) -> ReceivingCoordinateOut:
    """遗留补录入台：仅在发布时未固化坐标时允许一次写入，不得重写已固化快照。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        order = conn.execute(
            "SELECT id, status, recv_lat, recv_lon FROM orders "
            "WHERE id = ? AND shipper_id = ?",
            (order_id, shipper_id),
        ).fetchone()
        if order is None:
            raise OrderNotFoundError()
        if order["status"] not in ("待承接", "已承接"):
            raise SignoffRuleError("订单已起运，收货快照坐标不可修改")
        if order["recv_lat"] is not None and order["recv_lon"] is not None:
            raise SignoffRuleError("收货快照坐标已在发布时固化，不可重写")
        conn.execute(
            "UPDATE orders SET recv_lat = ?, recv_lon = ? WHERE id = ?",
            (payload.latitude, payload.longitude, order_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return ReceivingCoordinateOut(
        order_id=order_id, latitude=payload.latitude, longitude=payload.longitude
    )


# --- 司机侧 ---


def submit_arrival_checkin(
    conn: sqlite3.Connection,
    driver_id: int,
    task_id: int,
    payload: ArrivalCheckinIn,
    radius_m: int,
) -> ArrivalCheckinOut:
    """提交收货地打卡：超范围落告警与说明要求，不自动驳回；任务转待签收。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = checkin_service._driver_task(conn, driver_id, task_id)
        if task["status"] != "运输中":
            raise TaskStateError("任务当前状态不可收货打卡")
        distance: int | None = None
        if task["recv_lat"] is not None and task["recv_lon"] is not None:
            distance = int(
                round(
                    checkin_service._haversine_m(
                        task["recv_lat"],
                        task["recv_lon"],
                        payload.latitude,
                        payload.longitude,
                    )
                )
            )
        out_of_range = distance is not None and distance > radius_m
        position_status = "位置异常" if out_of_range else "正常"
        warning = ""
        if out_of_range:
            warning = f"当前定位距收货快照 {distance} 米，超出 {radius_m} 米范围，请提交位置异常说明。"
        cursor = conn.execute(
            """INSERT INTO arrival_checkins
               (task_id, order_id, driver_account_id, latitude, longitude, arrived_at,
                photos, notes, position_status, distance_m, reason, actor,
                replaced_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '司机', NULL, ?)""",
            (
                task_id,
                task["order_id"],
                driver_id,
                payload.latitude,
                payload.longitude,
                payload.arrived_at,
                json.dumps(payload.photos, ensure_ascii=False),
                payload.notes,
                position_status,
                distance,
                "首次打卡",
                now,
            ),
        )
        checkin_id = cursor.lastrowid
        conn.execute(
            "UPDATE transport_tasks SET status = '待签收' WHERE id = ?", (task_id,)
        )
        kind = "收货地打卡位置异常" if out_of_range else "收货地打卡"
        body = f"运输任务 {task['task_no']} 司机已到达收货地打卡。" + warning
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return ArrivalCheckinOut(
        id=checkin_id,
        task_id=task_id,
        task_no=task["task_no"],
        latitude=payload.latitude,
        longitude=payload.longitude,
        arrived_at=payload.arrived_at,
        photos=payload.photos,
        notes=payload.notes,
        position_status=position_status,
        distance_m=distance,
        warning=warning,
        exception_note_required=out_of_range,
        created_at=now,
    )


def submit_arrival_note(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: ArrivalNoteIn
) -> ArrivalNoteOut:
    """对收货地位置异常打卡补充说明，只读追加。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = checkin_service._driver_task(conn, driver_id, task_id)
        checkin = _latest_arrival_checkin(conn, task_id)
        if checkin is None:
            raise SignoffRuleError("请先提交收货地打卡")
        cursor = conn.execute(
            """INSERT INTO arrival_exception_notes
               (checkin_id, note, actor, replaced_by, created_at)
               VALUES (?, ?, '司机', NULL, ?)""",
            (checkin["id"], payload.note, now),
        )
        note_id = cursor.lastrowid
        kind = "收货异常说明"
        body = f"运输任务 {task['task_no']} 司机已提交收货地位置异常说明：{payload.note}"
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return ArrivalNoteOut(
        id=note_id, checkin_id=checkin["id"], note=payload.note, created_at=now
    )


def add_unloading_photos(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: UnloadingPhotosIn
) -> UnloadingPhotosOut:
    """上传某一卸货阶段的现场照片，只读追加。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = checkin_service._driver_task(conn, driver_id, task_id)
        if task["status"] not in ("运输中", "待签收"):
            raise TaskStateError("任务当前状态不可上传卸货照片")
        cursor = conn.execute(
            """INSERT INTO unloading_photos
               (task_id, driver_account_id, phase, paths, actor, replaced_by, created_at)
               VALUES (?, ?, ?, ?, '司机', NULL, ?)""",
            (
                task_id,
                driver_id,
                payload.phase,
                json.dumps(payload.paths, ensure_ascii=False),
                now,
            ),
        )
        photo_id = cursor.lastrowid
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return UnloadingPhotosOut(
        id=photo_id,
        task_id=task_id,
        phase=payload.phase,
        paths=payload.paths,
        created_at=now,
    )


def add_unloading_anomaly(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: UnloadingAnomalyIn
) -> UnloadingAnomalyOut:
    """上报卸货异常，只读追加并通知公司与货主。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = checkin_service._driver_task(conn, driver_id, task_id)
        if task["status"] not in ("运输中", "待签收"):
            raise TaskStateError("任务当前状态不可上报卸货异常")
        cursor = conn.execute(
            """INSERT INTO unloading_anomalies
               (task_id, driver_account_id, kind, detail, photos, actor, replaced_by, created_at)
               VALUES (?, ?, ?, ?, ?, '司机', NULL, ?)""",
            (
                task_id,
                driver_id,
                payload.kind,
                payload.detail,
                json.dumps(payload.photos, ensure_ascii=False),
                now,
            ),
        )
        anomaly_id = cursor.lastrowid
        kind = "卸货异常"
        body = f"运输任务 {task['task_no']} 上报卸货异常（{payload.kind}）：{payload.detail}"
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return UnloadingAnomalyOut(
        id=anomaly_id,
        task_id=task_id,
        kind=payload.kind,
        detail=payload.detail,
        photos=payload.photos,
        created_at=now,
    )


def submit_signoff(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: SignoffIn
) -> TaskProgressOut:
    """签收门禁：到达打卡、卸货照片与异常说明齐备后落签收凭证，任务转待确认完成。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = checkin_service._driver_task(conn, driver_id, task_id)
        if task["status"] != "待签收":
            raise TaskStateError("任务当前状态不可提交签收资料")
        checkin = _latest_arrival_checkin(conn, task_id)
        if checkin is None:
            raise SignoffRuleError("请先完成收货地打卡")
        if checkin["position_status"] == "位置异常":
            note = conn.execute(
                """SELECT id FROM arrival_exception_notes
                   WHERE checkin_id = ? AND replaced_by IS NULL LIMIT 1""",
                (checkin["id"],),
            ).fetchone()
            if note is None:
                raise SignoffRuleError("位置异常须先提交异常说明后方可提交签收资料")
        phases = {
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT phase FROM unloading_photos WHERE task_id = ?", (task_id,)
            )
        }
        missing = [phase for phase in _UNLOADING_PHASES if phase not in phases]
        if missing:
            raise SignoffRuleError("请先上传卸货前、卸货中与卸货完成照片")
        voucher_no = _voucher_no(conn, now)
        conn.execute(
            """INSERT INTO signoff_vouchers
               (voucher_no, task_id, order_id, driver_account_id, receiving_condition,
                received_at, receiver_name, signature_photos, vouchers, notes,
                actor, replaced_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '司机', NULL, ?)""",
            (
                voucher_no,
                task_id,
                task["order_id"],
                driver_id,
                payload.receiving_condition,
                payload.received_at,
                payload.receiver_name,
                json.dumps(payload.signature_photos, ensure_ascii=False),
                json.dumps(payload.vouchers, ensure_ascii=False),
                payload.notes,
                now,
            ),
        )
        conn.execute(
            "UPDATE transport_tasks SET status = '待确认完成' WHERE id = ?", (task_id,)
        )
        kind = "签收资料提交"
        body = f"运输任务 {task['task_no']} 司机已提交签收凭证 {voucher_no}，请核对确认。"
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, driver_id, "司机", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return checkin_service._progress(conn, checkin_service._driver_task(conn, driver_id, task_id))


# --- 物流公司侧 ---


def carrier_confirm(
    conn: sqlite3.Connection, carrier_id: int, task_id: int, payload: SignoffConfirmIn
) -> TaskProgressOut:
    """公司依据签收凭证确认完成：任务与订单同时转已完成，三方收到通知。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = checkin_service._carrier_task(conn, carrier_id, task_id)
        if task["status"] != "待确认完成":
            raise TaskStateError("任务当前状态不可确认完成")
        if not payload.confirmed:
            raise SignoffRuleError("请确认签收凭证无误")
        voucher = conn.execute(
            """SELECT id, voucher_no FROM signoff_vouchers
               WHERE task_id = ? AND replaced_by IS NULL ORDER BY id DESC LIMIT 1""",
            (task_id,),
        ).fetchone()
        if voucher is None:
            raise SignoffRuleError("缺少签收凭证，无法确认完成")
        conn.execute(
            """INSERT INTO signoff_confirmations
               (task_id, voucher_id, carrier_account_id, notes, actor, replaced_by, created_at)
               VALUES (?, ?, ?, ?, '物流公司', NULL, ?)""",
            (task_id, voucher["id"], carrier_id, payload.notes, now),
        )
        conn.execute(
            "UPDATE transport_tasks SET status = '已完成' WHERE id = ?", (task_id,)
        )
        conn.execute(
            "UPDATE orders SET status = '已完成' WHERE id = ?", (task["order_id"],)
        )
        kind = "运输完成"
        body = f"运输任务 {task['task_no']} 已依据签收凭证 {voucher['voucher_no']} 确认完成。"
        _notify(conn, task["driver_account_id"], "司机", kind, kind, body, task_id, now)
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return checkin_service._progress(conn, checkin_service._carrier_task(conn, carrier_id, task_id))
