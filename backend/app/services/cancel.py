"""订单取消业务：按状态分支申请、公司同意/驳回、通知与追加留痕。

未承接直接取消；已承接未起运进入取消处理中待公司处理；在途不提供取消入口，
仅由异常处理的「终止运输」置已取消。取消处理中与异常处理中互斥。
"""

import sqlite3
from datetime import datetime

from app.exceptions import (
    CancelApplicationNotFoundError,
    CancelRuleError,
    OrderNotFoundError,
)
from app.services.notify import notify
from app.schemas.cancel import (
    CancelApplyIn,
    CancelAuditOut,
    CancelOptionsOut,
    CancelOut,
    CancelRejectIn,
    CancelViewOut,
)

def _notify(
    conn: sqlite3.Connection,
    recipient_id: int,
    role: str,
    kind: str,
    body: str,
    related_id: int,
    now: str,
) -> None:
    """沿用本域既有调用签名；具体实现走统一通知写入。"""
    notify(conn, recipient_id, role, kind, kind, body, related_id, now)


_APP_SELECT = """
    SELECT a.id, a.application_no, a.order_id, a.shipper_id, a.carrier_id, a.mode,
           a.status, a.reason, a.handled_reason, a.before_status, a.after_status,
           a.handled_by, a.handled_at, a.created_at, a.updated_at,
           o.order_no, o.status AS current_order_status
    FROM cancel_applications a JOIN orders o ON o.id = a.order_id
"""

_IN_TRANSIT_TASK = ("运输中", "待签收", "异常")


def _now() -> tuple[datetime, str]:
    now_dt = datetime.now()
    return now_dt, now_dt.isoformat()


def _order_for_shipper(conn: sqlite3.Connection, shipper_id: int, order_id: int):
    """按当前货主读取订单，非本人记录视为不存在。"""
    row = conn.execute(
        """SELECT id, order_no, shipper_id, carrier_id, status, created_at
           FROM orders WHERE id = ? AND shipper_id = ?""",
        (order_id, shipper_id),
    ).fetchone()
    if row is None:
        raise OrderNotFoundError()
    return row


def _task_for_order(conn: sqlite3.Connection, order_id: int):
    """读取订单上最新一条运输任务，无派单返回 None。"""
    return conn.execute(
        """SELECT id, task_no, status, driver_account_id, cancel_status
           FROM transport_tasks WHERE order_id = ? ORDER BY id DESC LIMIT 1""",
        (order_id,),
    ).fetchone()


def _decision(status: str, task) -> tuple[bool, str | None, str]:
    """按订单状态与任务状态决定是否提供取消入口及取消方式。"""
    if status == "已完成":
        return False, None, "已完成运输不能取消"
    if status == "异常处理中":
        return False, None, "订单已进入异常处理中，请通过异常处理终止运输"
    if status == "取消处理中":
        return False, None, "订单已在取消处理中，不可重复申请"
    if status == "已取消":
        return False, None, "订单已取消，无需重复申请"
    if task is not None and task["status"] == "待确认完成":
        return False, None, "签收凭证待物流公司确认，不能取消订单"
    if status == "运输中" or (task is not None and task["status"] in _IN_TRANSIT_TASK):
        return False, None, "订单已开始运输，不提供取消入口，请通过异常处理终止运输"
    if status == "待承接":
        return True, "直接取消", ""
    return True, "公司确认", ""


def _audit(
    conn: sqlite3.Connection,
    application_id: int,
    order_id: int,
    event: str,
    actor_id: int,
    actor: str,
    from_status: str,
    to_status: str,
    reason: str,
    detail: str,
    now: str,
) -> None:
    """追加一条不可变的取消操作留痕。"""
    conn.execute(
        """INSERT INTO cancel_audit
           (application_id, order_id, event, actor_id, actor, from_status,
            to_status, reason, detail, created_at, replaced_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
        (
            application_id,
            order_id,
            event,
            actor_id,
            actor,
            from_status,
            to_status,
            reason,
            detail,
            now,
        ),
    )


def _out(conn: sqlite3.Connection, application_id: int) -> CancelOut:
    """把取消申请行组装为出参。"""
    row = conn.execute(_APP_SELECT + " WHERE a.id = ?", (application_id,)).fetchone()
    return CancelOut(
        id=row["id"],
        application_no=row["application_no"],
        order_id=row["order_id"],
        order_no=row["order_no"],
        shipper_id=row["shipper_id"],
        carrier_id=row["carrier_id"],
        mode=row["mode"],
        status=row["status"],
        reason=row["reason"],
        handled_reason=row["handled_reason"],
        before_status=row["before_status"],
        after_status=row["after_status"],
        handled_by=row["handled_by"],
        handled_at=row["handled_at"],
        created_at=row["created_at"],
    )


def _carrier_application(conn: sqlite3.Connection, carrier_id: int, application_id: int):
    """取当前公司承运订单上的取消申请，非本公司视为不存在。"""
    row = conn.execute(
        _APP_SELECT + " WHERE a.id = ? AND a.carrier_id = ?", (application_id, carrier_id)
    ).fetchone()
    if row is None:
        raise CancelApplicationNotFoundError()
    return row


# --- 货主侧 ---


def cancellation_options(
    conn: sqlite3.Connection, shipper_id: int, order_id: int
) -> CancelOptionsOut:
    """货主读取订单的取消入口可用性。"""
    order = _order_for_shipper(conn, shipper_id, order_id)
    task = _task_for_order(conn, order_id)
    can_cancel, mode, message = _decision(order["status"], task)
    return CancelOptionsOut(
        order_id=order_id,
        status=order["status"],
        can_cancel=can_cancel,
        mode=mode,
        message=message,
    )


def apply_cancel(
    conn: sqlite3.Connection, shipper_id: int, order_id: int, payload: CancelApplyIn
) -> CancelOut:
    """货主按订单状态申请取消：未承接直接取消，其余未起运进入取消处理中。"""
    _order_for_shipper(conn, shipper_id, order_id)
    conn.execute("BEGIN IMMEDIATE")
    try:
        order = _order_for_shipper(conn, shipper_id, order_id)
        task = _task_for_order(conn, order_id)
        can_cancel, mode, message = _decision(order["status"], task)
        if not can_cancel:
            raise CancelRuleError(message)

        reason = (payload.reason or "").strip()
        if mode == "公司确认" and not reason:
            raise CancelRuleError("取消原因必填")

        now_dt, now = _now()
        prefix = f"CANC-{now_dt.strftime('%y%m%d')}"
        used = conn.execute(
            "SELECT COUNT(*) FROM cancel_applications WHERE application_no LIKE ?",
            (f"{prefix}-%",),
        ).fetchone()[0]
        application_no = f"{prefix}-{used + 1:04d}"

        direct = mode == "直接取消"
        app_status = "已直接取消" if direct else "待公司处理"
        after_status = "已取消" if direct else None
        cursor = conn.execute(
            """INSERT INTO cancel_applications
               (application_no, order_id, shipper_id, carrier_id, mode, status,
                reason, handled_reason, before_status, after_status, handled_by,
                handled_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, '', ?, ?, NULL, NULL, ?, ?)""",
            (
                application_no,
                order_id,
                shipper_id,
                order["carrier_id"],
                mode,
                app_status,
                reason,
                order["status"],
                after_status,
                now,
                now,
            ),
        )
        application_id = cursor.lastrowid
        _audit(
            conn,
            application_id,
            order_id,
            "申请",
            shipper_id,
            "货主",
            order["status"],
            "已取消" if direct else "取消处理中",
            reason,
            "货主提交取消申请",
            now,
        )
        new_order_status = "已取消" if direct else "取消处理中"
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (new_order_status, order_id)
        )
        if direct:
            _audit(
                conn,
                application_id,
                order_id,
                "直接取消",
                shipper_id,
                "货主",
                order["status"],
                "已取消",
                "",
                "未承接订单由货主直接取消",
                now,
            )
            _notify(
                conn,
                shipper_id,
                "货主",
                "取消结果",
                f"运输订单 {order['order_no']} 已取消。",
                order_id,
                now,
            )
        else:
            if task is not None:
                conn.execute(
                    "UPDATE transport_tasks SET cancel_status = '取消中' WHERE id = ?",
                    (task["id"],),
                )
            if order["carrier_id"] is None:
                raise CancelRuleError("订单未承接，不能走公司确认取消")
            _notify(
                conn,
                order["carrier_id"],
                "物流公司",
                "取消申请",
                f"货主申请取消运输订单 {order['order_no']}，原因：{reason}，请处理。",
                order_id,
                now,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _out(conn, application_id)


def cancellation_view(
    conn: sqlite3.Connection, shipper_id: int, order_id: int
) -> CancelViewOut:
    """货主只读查看自己订单的取消申请与全过程留痕。"""
    _order_for_shipper(conn, shipper_id, order_id)
    applications = conn.execute(
        _APP_SELECT
        + " WHERE a.order_id = ? AND a.shipper_id = ? ORDER BY a.id DESC",
        (order_id, shipper_id),
    ).fetchall()
    audit_rows = conn.execute(
        """SELECT id, application_id, event, actor_id, actor, from_status,
                  to_status, reason, detail, created_at
           FROM cancel_audit WHERE order_id = ? ORDER BY id ASC""",
        (order_id,),
    ).fetchall()
    current = None
    if applications:
        row = applications[0]
        current = CancelOut(
            id=row["id"],
            application_no=row["application_no"],
            order_id=row["order_id"],
            order_no=row["order_no"],
            shipper_id=row["shipper_id"],
            carrier_id=row["carrier_id"],
            mode=row["mode"],
            status=row["status"],
            reason=row["reason"],
            handled_reason=row["handled_reason"],
            before_status=row["before_status"],
            after_status=row["after_status"],
            handled_by=row["handled_by"],
            handled_at=row["handled_at"],
            created_at=row["created_at"],
        )
    return CancelViewOut(
        application=current,
        audit=[
            CancelAuditOut(
                id=row["id"],
                application_id=row["application_id"],
                event=row["event"],
                actor_id=row["actor_id"],
                actor=row["actor"],
                from_status=row["from_status"],
                to_status=row["to_status"],
                reason=row["reason"],
                detail=row["detail"],
                created_at=row["created_at"],
            )
            for row in audit_rows
        ],
    )


# --- 物流公司侧 ---


def carrier_applications(conn: sqlite3.Connection, carrier_id: int) -> list[CancelOut]:
    """物流公司列出本公司承运订单上的全部取消申请。"""
    rows = conn.execute(
        _APP_SELECT + " WHERE a.carrier_id = ? ORDER BY a.id DESC", (carrier_id,)
    ).fetchall()
    return [
        CancelOut(
            id=row["id"],
            application_no=row["application_no"],
            order_id=row["order_id"],
            order_no=row["order_no"],
            shipper_id=row["shipper_id"],
            carrier_id=row["carrier_id"],
            mode=row["mode"],
            status=row["status"],
            reason=row["reason"],
            handled_reason=row["handled_reason"],
            before_status=row["before_status"],
            after_status=row["after_status"],
            handled_by=row["handled_by"],
            handled_at=row["handled_at"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def carrier_application_view(
    conn: sqlite3.Connection, carrier_id: int, application_id: int
) -> CancelViewOut:
    """物流公司读取一条取消申请的当前态与全过程留痕。"""
    app = _carrier_application(conn, carrier_id, application_id)
    audit_rows = conn.execute(
        """SELECT id, application_id, event, actor_id, actor, from_status,
                  to_status, reason, detail, created_at
           FROM cancel_audit WHERE order_id = ? ORDER BY id ASC""",
        (app["order_id"],),
    ).fetchall()
    return CancelViewOut(
        application=_out(conn, application_id),
        audit=[
            CancelAuditOut(
                id=row["id"],
                application_id=row["application_id"],
                event=row["event"],
                actor_id=row["actor_id"],
                actor=row["actor"],
                from_status=row["from_status"],
                to_status=row["to_status"],
                reason=row["reason"],
                detail=row["detail"],
                created_at=row["created_at"],
            )
            for row in audit_rows
        ],
    )


def agree_cancel(
    conn: sqlite3.Connection, carrier_id: int, application_id: int
) -> CancelOut:
    """物流公司同意取消：订单置已取消，追加同意留痕并通知货主。"""
    _carrier_application(conn, carrier_id, application_id)
    conn.execute("BEGIN IMMEDIATE")
    try:
        app = _carrier_application(conn, carrier_id, application_id)
        if app["status"] != "待公司处理":
            raise CancelRuleError("取消申请当前状态不允许同意")
        if app["current_order_status"] != "取消处理中":
            raise CancelRuleError("订单不处于取消处理中，不能同意取消")

        now_dt, now = _now()
        conn.execute(
            "UPDATE orders SET status = '已取消' WHERE id = ?", (app["order_id"],)
        )
        conn.execute(
            """UPDATE cancel_applications
               SET status = '已同意', after_status = '已取消', handled_by = ?,
                   handled_at = ?, updated_at = ? WHERE id = ?""",
            (carrier_id, now, now, application_id),
        )
        _audit(
            conn,
            application_id,
            app["order_id"],
            "同意",
            carrier_id,
            "物流公司",
            "取消处理中",
            "已取消",
            "",
            "公司同意取消，订单已取消",
            now,
        )
        conn.execute(
            "UPDATE transport_tasks SET cancel_status = '已取消' WHERE order_id = ?",
            (app["order_id"],),
        )
        # 取消生效后释放司机与车辆占用，避免资源被永久锁死
        task = conn.execute(
            "SELECT driver_account_id, vehicle_id FROM transport_tasks "
            "WHERE order_id = ? ORDER BY id DESC LIMIT 1",
            (app["order_id"],),
        ).fetchone()
        if task is not None:
            from app.services.exception import _set_occupancy

            _set_occupancy(
                conn, task["driver_account_id"], task["vehicle_id"], occupy=False
            )
        _notify(
            conn,
            app["shipper_id"],
            "货主",
            "取消结果",
            f"物流公司已同意取消运输订单 {app['order_no']}，订单已取消。",
            app["order_id"],
            now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _out(conn, application_id)


def reject_cancel(
    conn: sqlite3.Connection, carrier_id: int, application_id: int, payload: CancelRejectIn
) -> CancelOut:
    """物流公司驳回取消：订单恢复申请前状态，原因写明并通知货主。"""
    reason = payload.reason.strip()
    if not reason:
        raise CancelRuleError("驳回原因必填")

    _carrier_application(conn, carrier_id, application_id)
    conn.execute("BEGIN IMMEDIATE")
    try:
        app = _carrier_application(conn, carrier_id, application_id)
        if app["status"] != "待公司处理":
            raise CancelRuleError("取消申请当前状态不允许驳回")
        if app["current_order_status"] != "取消处理中":
            raise CancelRuleError("订单不处于取消处理中，不能驳回取消")

        now_dt, now = _now()
        restore = app["before_status"]
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (restore, app["order_id"])
        )
        conn.execute(
            """UPDATE cancel_applications
               SET status = '已驳回', after_status = ?, handled_reason = ?,
                   handled_by = ?, handled_at = ?, updated_at = ? WHERE id = ?""",
            (restore, reason, carrier_id, now, now, application_id),
        )
        _audit(
            conn,
            application_id,
            app["order_id"],
            "驳回",
            carrier_id,
            "物流公司",
            "取消处理中",
            restore,
            reason,
            "公司驳回取消申请，订单恢复申请前状态",
            now,
        )
        conn.execute(
            "UPDATE transport_tasks SET cancel_status = '' WHERE order_id = ?",
            (app["order_id"],),
        )
        _notify(
            conn,
            app["shipper_id"],
            "货主",
            "取消结果",
            f"物流公司驳回运输订单 {app['order_no']} 的取消申请，"
            f"原因：{reason}，订单已恢复至{restore}。",
            app["order_id"],
            now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _out(conn, application_id)
