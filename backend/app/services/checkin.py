"""打卡业务：位置校验、装货凭证、起运门禁与关键节点通知。"""

import json
import math
import sqlite3
from datetime import datetime, timezone

from app.exceptions import (
    CheckinRuleError,
    OrderNotFoundError,
    TaskNotFoundError,
    TaskStateError,
)
from app.schemas.checkin import (
    CheckinIn,
    CheckinOut,
    DepartureConfirmationOut,
    ExceptionNoteIn,
    ExceptionNoteOut,
    LoadingAnomalyIn,
    LoadingAnomalyOut,
    LoadingPhotosIn,
    LoadingPhotosOut,
    SiteCoordinateIn,
    SiteCoordinateOut,
    StartTransportIn,
    TaskProgressOut,
)
from app.schemas.signoff import (
    ArrivalCheckinOut,
    ArrivalNoteOut,
    SignoffConfirmationOut,
    SignoffVoucherOut,
    UnloadingAnomalyOut,
    UnloadingPhotosOut,
)

_LOADING_PHASES = ("装货前", "装货中", "装货完成")

_TASK_SELECT = """
    SELECT t.id, t.task_no, t.order_id, o.order_no, t.status, t.carrier_id,
           t.driver_account_id, o.shipper_id, o.status AS order_status, o.ship_lat, o.ship_lon,
           o.recv_lat, o.recv_lon, t.planned_load_at, t.planned_deliver_at
    FROM transport_tasks t JOIN orders o ON o.id = t.order_id
"""

_CHECKIN_SELECT = """
    SELECT c.*, t.task_no
    FROM departure_checkins c JOIN transport_tasks t ON t.id = c.task_id
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """两点间球面直线距离，单位米。"""
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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
    """取当前货主订单上的运输任务；非本人订单视为不可见。"""
    row = conn.execute(
        _TASK_SELECT + " WHERE o.shipper_id = ? AND o.id = ? ORDER BY t.id DESC LIMIT 1",
        (shipper_id, order_id),
    ).fetchone()
    if row is None:
        raise TaskNotFoundError()
    return row


def _checkin_out(row, task_no: str) -> CheckinOut:
    """把打卡行转为出参，并携带超范围告警。"""
    distance = row["distance_m"]
    out_of_range = row["position_status"] == "位置异常"
    warning = ""
    if out_of_range:
        warning = f"当前定位超出发货地允许范围（{distance} 米），请提交位置异常说明。"
    return CheckinOut(
        id=row["id"],
        task_id=row["task_id"],
        task_no=task_no,
        latitude=row["latitude"],
        longitude=row["longitude"],
        arrived_at=row["arrived_at"],
        photos=json.loads(row["photos"]),
        notes=row["notes"],
        position_status=row["position_status"],
        distance_m=distance,
        warning=warning,
        exception_note_required=out_of_range,
        created_at=row["created_at"],
    )


def _arrival_checkin_out(row, task_no: str) -> ArrivalCheckinOut:
    """把收货地打卡行转为出参，并携带超范围告警。"""
    distance = row["distance_m"]
    out_of_range = row["position_status"] == "位置异常"
    warning = ""
    if out_of_range:
        warning = f"当前定位超收货地允许范围（{distance} 米），请提交位置异常说明。"
    return ArrivalCheckinOut(
        id=row["id"],
        task_id=row["task_id"],
        task_no=task_no,
        latitude=row["latitude"],
        longitude=row["longitude"],
        arrived_at=row["arrived_at"],
        photos=json.loads(row["photos"]),
        notes=row["notes"],
        position_status=row["position_status"],
        distance_m=distance,
        warning=warning,
        exception_note_required=out_of_range,
        created_at=row["created_at"],
    )


def _latest_checkin(conn: sqlite3.Connection, task_id: int):
    """取任务当前有效打卡（只读追加，replaced_by 为空）。"""
    return conn.execute(
        _CHECKIN_SELECT
        + " WHERE c.task_id = ? AND c.replaced_by IS NULL ORDER BY c.id DESC LIMIT 1",
        (task_id,),
    ).fetchone()


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


def _progress(conn: sqlite3.Connection, task) -> TaskProgressOut:
    """把任务的打卡与装货记录汇总为进度视图。"""
    task_id = task["id"]
    fresh_task = conn.execute(
        "SELECT task_no, status, planned_load_at, planned_deliver_at FROM transport_tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    order_status = conn.execute(
        "SELECT status FROM orders WHERE id = ?", (task["order_id"],)
    ).fetchone()["status"]

    checkins = [
        _checkin_out(row, fresh_task["task_no"])
        for row in conn.execute(
            _CHECKIN_SELECT + " WHERE c.task_id = ? ORDER BY c.id ASC", (task_id,)
        )
    ]
    notes = [
        ExceptionNoteOut(
            id=row["id"],
            checkin_id=row["checkin_id"],
            note=row["note"],
            created_at=row["created_at"],
        )
        for row in conn.execute(
            """SELECT id, checkin_id, note, created_at FROM checkin_exception_notes
               WHERE replaced_by IS NULL AND checkin_id IN
                 (SELECT id FROM departure_checkins WHERE task_id = ?)
               ORDER BY id ASC""",
            (task_id,),
        )
    ]
    photos = [
        LoadingPhotosOut(
            id=row["id"],
            task_id=row["task_id"],
            phase=row["phase"],
            paths=json.loads(row["paths"]),
            created_at=row["created_at"],
        )
        for row in conn.execute(
            """SELECT id, task_id, phase, paths, created_at FROM loading_photos
               WHERE task_id = ? AND replaced_by IS NULL ORDER BY id ASC""",
            (task_id,),
        )
    ]
    anomalies = [
        LoadingAnomalyOut(
            id=row["id"],
            task_id=row["task_id"],
            kind=row["kind"],
            detail=row["detail"],
            photos=json.loads(row["photos"]),
            created_at=row["created_at"],
        )
        for row in conn.execute(
            """SELECT id, task_id, kind, detail, photos, created_at FROM loading_anomalies
               WHERE task_id = ? AND replaced_by IS NULL ORDER BY id ASC""",
            (task_id,),
        )
    ]
    confirmation_row = conn.execute(
        """SELECT id, task_id, cargo_confirmed, vehicle_confirmed, notes, created_at
           FROM departure_confirmations
           WHERE task_id = ? AND replaced_by IS NULL ORDER BY id DESC LIMIT 1""",
        (task_id,),
    ).fetchone()
    confirmation = None
    if confirmation_row is not None:
        confirmation = DepartureConfirmationOut(
            id=confirmation_row["id"],
            task_id=confirmation_row["task_id"],
            cargo_confirmed=bool(confirmation_row["cargo_confirmed"]),
            vehicle_confirmed=bool(confirmation_row["vehicle_confirmed"]),
            notes=confirmation_row["notes"],
            created_at=confirmation_row["created_at"],
        )
    arrival_checkins = [
        _arrival_checkin_out(row, fresh_task["task_no"])
        for row in conn.execute(
            """SELECT * FROM arrival_checkins
               WHERE task_id = ? AND replaced_by IS NULL ORDER BY id ASC""",
            (task_id,),
        )
    ]
    arrival_notes = [
        ArrivalNoteOut(
            id=row["id"],
            checkin_id=row["checkin_id"],
            note=row["note"],
            created_at=row["created_at"],
        )
        for row in conn.execute(
            """SELECT id, checkin_id, note, created_at FROM arrival_exception_notes
               WHERE replaced_by IS NULL AND checkin_id IN
                 (SELECT id FROM arrival_checkins WHERE task_id = ?)
               ORDER BY id ASC""",
            (task_id,),
        )
    ]
    unloading_photos = [
        UnloadingPhotosOut(
            id=row["id"],
            task_id=row["task_id"],
            phase=row["phase"],
            paths=json.loads(row["paths"]),
            created_at=row["created_at"],
        )
        for row in conn.execute(
            """SELECT id, task_id, phase, paths, created_at FROM unloading_photos
               WHERE task_id = ? AND replaced_by IS NULL ORDER BY id ASC""",
            (task_id,),
        )
    ]
    unloading_anomalies = [
        UnloadingAnomalyOut(
            id=row["id"],
            task_id=row["task_id"],
            kind=row["kind"],
            detail=row["detail"],
            photos=json.loads(row["photos"]),
            created_at=row["created_at"],
        )
        for row in conn.execute(
            """SELECT id, task_id, kind, detail, photos, created_at FROM unloading_anomalies
               WHERE task_id = ? AND replaced_by IS NULL ORDER BY id ASC""",
            (task_id,),
        )
    ]
    voucher_row = conn.execute(
        """SELECT * FROM signoff_vouchers
           WHERE task_id = ? AND replaced_by IS NULL ORDER BY id DESC LIMIT 1""",
        (task_id,),
    ).fetchone()
    voucher = None
    if voucher_row is not None:
        voucher = SignoffVoucherOut(
            id=voucher_row["id"],
            voucher_no=voucher_row["voucher_no"],
            task_id=voucher_row["task_id"],
            task_no=fresh_task["task_no"],
            order_id=voucher_row["order_id"],
            receiving_condition=voucher_row["receiving_condition"],
            received_at=voucher_row["received_at"],
            receiver_name=voucher_row["receiver_name"],
            signature_photos=json.loads(voucher_row["signature_photos"]),
            vouchers=json.loads(voucher_row["vouchers"]),
            notes=voucher_row["notes"],
            created_at=voucher_row["created_at"],
        )
    signoff_row = conn.execute(
        """SELECT id, task_id, voucher_id, carrier_account_id, notes, created_at
           FROM signoff_confirmations
           WHERE task_id = ? AND replaced_by IS NULL ORDER BY id DESC LIMIT 1""",
        (task_id,),
    ).fetchone()
    signoff_confirmation = None
    if signoff_row is not None:
        signoff_confirmation = SignoffConfirmationOut(
            id=signoff_row["id"],
            task_id=signoff_row["task_id"],
            voucher_id=signoff_row["voucher_id"],
            carrier_account_id=signoff_row["carrier_account_id"],
            notes=signoff_row["notes"],
            created_at=signoff_row["created_at"],
        )
    return TaskProgressOut(
        task_id=task_id,
        task_no=fresh_task["task_no"],
        order_id=task["order_id"],
        order_no=task["order_no"],
        status=fresh_task["status"],
        task_status=fresh_task["status"],
        order_status=order_status,
        planned_load_at=fresh_task["planned_load_at"],
        planned_deliver_at=fresh_task["planned_deliver_at"],
        checkins=checkins,
        exception_notes=notes,
        loading_photos=photos,
        loading_anomalies=anomalies,
        confirmation=confirmation,
        arrival_checkins=arrival_checkins,
        arrival_notes=arrival_notes,
        unloading_photos=unloading_photos,
        unloading_anomalies=unloading_anomalies,
        signoff_voucher=voucher,
        signoff_confirmation=signoff_confirmation,
    )


# --- 司机侧 ---


def submit_checkin(
    conn: sqlite3.Connection,
    driver_id: int,
    task_id: int,
    payload: CheckinIn,
    radius_m: int,
) -> CheckinOut:
    """提交发货地打卡：超范围落告警与说明要求，不自动驳回。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = _driver_task(conn, driver_id, task_id)
        if task["status"] != "待装货":
            raise TaskStateError("任务当前状态不可打卡")
        distance: int | None = None
        if task["ship_lat"] is not None and task["ship_lon"] is not None:
            distance = int(
                round(
                    _haversine_m(
                        task["ship_lat"],
                        task["ship_lon"],
                        payload.latitude,
                        payload.longitude,
                    )
                )
            )
        out_of_range = distance is not None and distance > radius_m
        position_status = "位置异常" if out_of_range else "正常"
        warning = ""
        if out_of_range:
            warning = f"当前定位距发货快照 {distance} 米，超出 {radius_m} 米范围，请提交位置异常说明。"
        cursor = conn.execute(
            """INSERT INTO departure_checkins
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
        kind = "发货地打卡位置异常" if out_of_range else "发货地打卡"
        body = f"运输任务 {task['task_no']} 司机已到达发货地打卡。" + warning
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return CheckinOut(
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


def submit_exception_note(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: ExceptionNoteIn
) -> ExceptionNoteOut:
    """对位置异常打卡补充说明，只读追加。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = _driver_task(conn, driver_id, task_id)
        checkin = _latest_checkin(conn, task_id)
        if checkin is None:
            raise CheckinRuleError("请先提交发货地打卡")
        cursor = conn.execute(
            """INSERT INTO checkin_exception_notes
               (checkin_id, note, actor, replaced_by, created_at)
               VALUES (?, ?, '司机', NULL, ?)""",
            (checkin["id"], payload.note, now),
        )
        note_id = cursor.lastrowid
        kind = "打卡异常说明"
        body = f"运输任务 {task['task_no']} 司机已提交位置异常说明：{payload.note}"
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return ExceptionNoteOut(
        id=note_id, checkin_id=checkin["id"], note=payload.note, created_at=now
    )


def add_loading_photos(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: LoadingPhotosIn
) -> LoadingPhotosOut:
    """上传某一装货阶段的现场照片，只读追加。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = _driver_task(conn, driver_id, task_id)
        if task["status"] != "待装货":
            raise TaskStateError("任务当前状态不可上传装货照片")
        cursor = conn.execute(
            """INSERT INTO loading_photos
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
    return LoadingPhotosOut(
        id=photo_id,
        task_id=task_id,
        phase=payload.phase,
        paths=payload.paths,
        created_at=now,
    )


def add_loading_anomaly(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: LoadingAnomalyIn
) -> LoadingAnomalyOut:
    """上报装货异常，只读追加并通知公司与货主。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = _driver_task(conn, driver_id, task_id)
        if task["status"] != "待装货":
            raise TaskStateError("任务当前状态不可上报装货异常")
        cursor = conn.execute(
            """INSERT INTO loading_anomalies
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
        kind = "装货异常"
        body = f"运输任务 {task['task_no']} 上报装货异常（{payload.kind}）：{payload.detail}"
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return LoadingAnomalyOut(
        id=anomaly_id,
        task_id=task_id,
        kind=payload.kind,
        detail=payload.detail,
        photos=payload.photos,
        created_at=now,
    )


def start_transport(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: StartTransportIn
) -> TaskProgressOut:
    """起运门禁：打卡、异常说明、装货凭证与核对确认齐备后推进任务与订单状态。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = _driver_task(conn, driver_id, task_id)
        if task["status"] != "待装货":
            raise TaskStateError("任务当前状态不可起运")
        checkin = _latest_checkin(conn, task_id)
        if checkin is None:
            raise CheckinRuleError("请先完成发货地打卡")
        if checkin["position_status"] == "位置异常":
            note = conn.execute(
                """SELECT id FROM checkin_exception_notes
                   WHERE checkin_id = ? AND replaced_by IS NULL LIMIT 1""",
                (checkin["id"],),
            ).fetchone()
            if note is None:
                raise CheckinRuleError("位置异常须先提交异常说明后方可起运")
        phases = {
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT phase FROM loading_photos WHERE task_id = ?", (task_id,)
            )
        }
        missing = [phase for phase in _LOADING_PHASES if phase not in phases]
        if missing:
            raise CheckinRuleError("请先上传装货前、装货中与装货完成照片")
        if not payload.cargo_confirmed or not payload.vehicle_confirmed:
            raise CheckinRuleError("请确认货物与车辆均已核对")
        conn.execute(
            """INSERT INTO departure_confirmations
               (task_id, driver_account_id, cargo_confirmed, vehicle_confirmed,
                notes, actor, replaced_by, created_at)
               VALUES (?, ?, ?, ?, ?, '司机', NULL, ?)""",
            (
                task_id,
                driver_id,
                int(payload.cargo_confirmed),
                int(payload.vehicle_confirmed),
                payload.notes,
                now,
            ),
        )
        conn.execute(
            "UPDATE transport_tasks SET status = '运输中' WHERE id = ?", (task_id,)
        )
        conn.execute(
            "UPDATE orders SET status = '运输中' WHERE id = ?", (task["order_id"],)
        )
        kind = "开始运输"
        body = f"运输任务 {task['task_no']} 已起运，进入运输中。"
        _notify(conn, driver_id, "司机", kind, kind, body, task_id, now)
        _notify(conn, task["carrier_id"], "物流公司", kind, kind, body, task_id, now)
        _notify(conn, task["shipper_id"], "货主", kind, kind, body, task_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _progress(conn, _driver_task(conn, driver_id, task_id))


# --- 物流公司 / 货主侧 ---


def set_site_coordinate(
    conn: sqlite3.Connection, shipper_id: int, order_id: int, payload: SiteCoordinateIn
) -> SiteCoordinateOut:
    """货主在起运前补录发货快照坐标，供位置打卡比对。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        order = conn.execute(
            "SELECT id, status FROM orders WHERE id = ? AND shipper_id = ?",
            (order_id, shipper_id),
        ).fetchone()
        if order is None:
            raise OrderNotFoundError()
        if order["status"] not in ("待承接", "已承接"):
            raise CheckinRuleError("订单已起运，发货快照坐标不可修改")
        conn.execute(
            "UPDATE orders SET ship_lat = ?, ship_lon = ? WHERE id = ?",
            (payload.latitude, payload.longitude, order_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return SiteCoordinateOut(
        order_id=order_id, latitude=payload.latitude, longitude=payload.longitude
    )


def carrier_progress(
    conn: sqlite3.Connection, carrier_id: int, task_id: int
) -> TaskProgressOut:
    """物流公司读取本公司任务的打卡与装货进度。"""
    return _progress(conn, _carrier_task(conn, carrier_id, task_id))


def shipper_progress(
    conn: sqlite3.Connection, shipper_id: int, order_id: int
) -> TaskProgressOut:
    """货主只读查看自己订单的运输进度。"""
    return _progress(conn, _shipper_task(conn, shipper_id, order_id))


def driver_progress(
    conn: sqlite3.Connection, driver_id: int, task_id: int
) -> TaskProgressOut:
    """司机读取本人任务的打卡与装货进度，不含运费报价。"""
    return _progress(conn, _driver_task(conn, driver_id, task_id))
