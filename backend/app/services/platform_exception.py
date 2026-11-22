"""平台异常管理与车辆转籍业务：只追加处理与转籍历史，不改写业务实体。"""

import sqlite3
from datetime import datetime

from app.exceptions import (
    AccountNotFoundError,
    OrderNotFoundError,
    PlatformExceptionNotFoundError,
    TaskNotFoundError,
    VehicleNotFoundError,
    VehicleTransferRuleError,
)
from app.schemas.platform_exception import (
    PlatformExceptionIn,
    PlatformExceptionOut,
    PlatformExceptionViewOut,
    PlatformHandlingIn,
    PlatformHandlingOut,
    VehicleTransferIn,
    VehicleTransferOut,
)

_IN_PROGRESS_TASK_STATUSES = ("待司机确认", "待装货", "运输中", "待签收", "待确认完成", "异常")

_EXCEPTION_SELECT = """
    SELECT id, exception_no, category, subject, detail, subject_account_id,
           order_id, task_id, vehicle_id, actor_id, actor, created_at
    FROM platform_exceptions
"""

_HANDLING_SELECT = """
    SELECT id, handling_no, exception_id, result, reason, detail, actor_id, actor,
           order_status, task_status, handled_at, created_at
    FROM platform_exception_handling
"""

_TRANSFER_SELECT = """
    SELECT id, transfer_no, vehicle_id, plate_no, before_carrier_id, after_carrier_id,
           reason, actor_id, actor, created_at
    FROM vehicle_transfers
"""


def _now_dt() -> datetime:
    return datetime.now()


def _next_no(
    conn: sqlite3.Connection, table: str, column: str, prefix: str, now_dt: datetime
) -> str:
    """按 prefix-YYMMDD-0001 生成当日不重复编号。"""
    head = f"{prefix}-{now_dt.strftime('%y%m%d')}"
    used = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {column} LIKE ?", (f"{head}-%",)
    ).fetchone()[0]
    return f"{head}-{used + 1:04d}"


def _exception_row(conn: sqlite3.Connection, exception_id: int):
    """取平台异常登记记录；不存在抛领域异常。"""
    row = conn.execute(_EXCEPTION_SELECT + " WHERE id = ?", (exception_id,)).fetchone()
    if row is None:
        raise PlatformExceptionNotFoundError()
    return row


def _exception_out(row) -> PlatformExceptionOut:
    return PlatformExceptionOut(
        id=row["id"],
        exception_no=row["exception_no"],
        category=row["category"],
        subject=row["subject"],
        detail=row["detail"],
        subject_account_id=row["subject_account_id"],
        order_id=row["order_id"],
        task_id=row["task_id"],
        vehicle_id=row["vehicle_id"],
        actor=row["actor"],
        created_at=row["created_at"],
    )


def _handling_out(row) -> PlatformHandlingOut:
    return PlatformHandlingOut(
        id=row["id"],
        handling_no=row["handling_no"],
        exception_id=row["exception_id"],
        result=row["result"],
        reason=row["reason"],
        detail=row["detail"],
        actor=row["actor"],
        actor_id=row["actor_id"],
        order_status=row["order_status"],
        task_status=row["task_status"],
        handled_at=row["handled_at"],
        created_at=row["created_at"],
    )


def _transfer_out(row) -> VehicleTransferOut:
    return VehicleTransferOut(
        id=row["id"],
        transfer_no=row["transfer_no"],
        vehicle_id=row["vehicle_id"],
        plate_no=row["plate_no"],
        before_carrier_id=row["before_carrier_id"],
        after_carrier_id=row["after_carrier_id"],
        reason=row["reason"],
        actor=row["actor"],
        actor_id=row["actor_id"],
        created_at=row["created_at"],
    )


def _view(conn: sqlite3.Connection, row) -> PlatformExceptionViewOut:
    """把平台异常与全部追加处理记录汇总为只读视图。"""
    handling = [
        _handling_out(item)
        for item in conn.execute(
            _HANDLING_SELECT + " WHERE exception_id = ? ORDER BY id ASC", (row["id"],)
        )
    ]
    return PlatformExceptionViewOut(exception=_exception_out(row), handling_records=handling)


def _notify(
    conn: sqlite3.Connection,
    account_id: int,
    kind: str,
    title: str,
    body: str,
    related_id: int,
    now: str,
) -> None:
    """平台异常 / 转籍结果写入业务站内信（与公告 / 通知内容通道隔离）。"""
    account = conn.execute("SELECT role FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if account is None:
        return
    conn.execute(
        """INSERT INTO notifications
           (recipient_id, recipient_role, kind, title, body, related_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (account_id, account["role"], kind, title, body, related_id, now),
    )


def _assert_refs(conn: sqlite3.Connection, payload: PlatformExceptionIn) -> None:
    """校验可选关联记录存在；缺失时给出明确的 404 语义。"""
    checks = (
        (payload.subject_account_id, "accounts", AccountNotFoundError),
        (payload.order_id, "orders", OrderNotFoundError),
        (payload.task_id, "transport_tasks", TaskNotFoundError),
        (payload.vehicle_id, "vehicles", VehicleNotFoundError),
    )
    for value, table, error in checks:
        if value is not None and not conn.execute(
            f"SELECT 1 FROM {table} WHERE id = ?", (value,)
        ).fetchone():
            raise error()


def create_exception(
    conn: sqlite3.Connection, admin_id: int, payload: PlatformExceptionIn
) -> PlatformExceptionOut:
    """管理员登记平台异常，作为后续追加处理记录的原始记录。"""
    now_dt = _now_dt()
    now = now_dt.isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        _assert_refs(conn, payload)
        exception_no = _next_no(
            conn, "platform_exceptions", "exception_no", "PFEXC", now_dt
        )
        cursor = conn.execute(
            """INSERT INTO platform_exceptions
               (exception_no, category, subject, detail, subject_account_id,
                order_id, task_id, vehicle_id, actor_id, actor, replaced_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '管理员', NULL, ?)""",
            (
                exception_no,
                payload.category,
                payload.subject,
                payload.detail,
                payload.subject_account_id,
                payload.order_id,
                payload.task_id,
                payload.vehicle_id,
                admin_id,
                now,
            ),
        )
        exception_id = cursor.lastrowid
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _exception_out(_exception_row(conn, exception_id))


def append_handling(
    conn: sqlite3.Connection,
    admin_id: int,
    exception_id: int,
    payload: PlatformHandlingIn,
) -> PlatformHandlingOut:
    """追加一条平台异常处理记录；原异常与其它处理记录均不改写。"""
    now_dt = _now_dt()
    now = now_dt.isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        exception = _exception_row(conn, exception_id)
        order_status = None
        task_status = None
        if exception["order_id"] is not None:
            order = conn.execute(
                "SELECT status FROM orders WHERE id = ?", (exception["order_id"],)
            ).fetchone()
            order_status = order["status"] if order else None
        if exception["task_id"] is not None:
            task = conn.execute(
                "SELECT status FROM transport_tasks WHERE id = ?", (exception["task_id"],)
            ).fetchone()
            task_status = task["status"] if task else None

        handling_no = _next_no(
            conn, "platform_exception_handling", "handling_no", "PFH", now_dt
        )
        cursor = conn.execute(
            """INSERT INTO platform_exception_handling
               (handling_no, exception_id, result, reason, detail, actor_id, actor,
                order_status, task_status, handled_at, replaced_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, '管理员', ?, ?, ?, NULL, ?)""",
            (
                handling_no,
                exception_id,
                payload.result,
                payload.reason,
                payload.detail,
                admin_id,
                order_status,
                task_status,
                now,
                now,
            ),
        )
        handling_id = cursor.lastrowid
        if exception["subject_account_id"] is not None:
            title = f"平台异常处理结果（{exception['category']}）"
            body = (
                f"平台异常“{exception['subject']}”处理结果：{payload.result}。"
                f"原因：{payload.reason}"
            )
            _notify(
                conn,
                exception["subject_account_id"],
                "平台异常处理结果",
                title,
                body,
                exception_id,
                now,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    row = conn.execute(
        _HANDLING_SELECT + " WHERE id = ?", (handling_id,)
    ).fetchone()
    return _handling_out(row)


def list_exceptions(
    conn: sqlite3.Connection, category: str | None = None
) -> list[PlatformExceptionOut]:
    """按类别列出平台异常登记记录。"""
    if category:
        rows = conn.execute(
            _EXCEPTION_SELECT + " WHERE category = ? ORDER BY id ASC", (category,)
        ).fetchall()
    else:
        rows = conn.execute(_EXCEPTION_SELECT + " ORDER BY id ASC").fetchall()
    return [_exception_out(row) for row in rows]


def get_exception(conn: sqlite3.Connection, exception_id: int) -> PlatformExceptionViewOut:
    """读取单条平台异常及其全部追加处理记录。"""
    return _view(conn, _exception_row(conn, exception_id))


def _in_progress_task(
    conn: sqlite3.Connection, vehicle_id: int
):
    """取占用该车辆的一条进行中运输任务；没有则返回 None。"""
    placeholders = ",".join("?" for _ in _IN_PROGRESS_TASK_STATUSES)
    return conn.execute(
        f"SELECT task_no, status FROM transport_tasks "
        f"WHERE vehicle_id = ? AND status IN ({placeholders}) "
        "AND cancel_status != '已取消' ORDER BY id LIMIT 1",
        (vehicle_id, *_IN_PROGRESS_TASK_STATUSES),
    ).fetchone()


def transfer_vehicle(
    conn: sqlite3.Connection, admin_id: int, payload: VehicleTransferIn
) -> VehicleTransferOut:
    """转籍：仅在车辆无进行中任务时改归属并追加前后留痕，不动历史任务车辆。"""
    now_dt = _now_dt()
    now = now_dt.isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        vehicle = conn.execute(
            "SELECT id, plate_no, carrier_id FROM vehicles WHERE id = ?", (payload.vehicle_id,)
        ).fetchone()
        if vehicle is None:
            raise VehicleNotFoundError()
        carrier = conn.execute(
            "SELECT id FROM accounts WHERE id = ? AND role = '物流公司'",
            (payload.to_carrier_id,),
        ).fetchone()
        if carrier is None:
            raise AccountNotFoundError()

        # 进行中任务（完成 / 拒绝为终态）占用车辆时禁止转籍
        active_task = _in_progress_task(conn, payload.vehicle_id)
        if active_task is not None:
            raise VehicleTransferRuleError(
                f"车辆存在进行中运输任务（{active_task['task_no']}，状态 "
                f"{active_task['status']}），不可转籍"
            )

        transfer_no = _next_no(conn, "vehicle_transfers", "transfer_no", "TR", now_dt)
        cursor = conn.execute(
            """INSERT INTO vehicle_transfers
               (transfer_no, vehicle_id, plate_no, before_carrier_id, after_carrier_id,
                reason, actor_id, actor, replaced_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, '管理员', NULL, ?)""",
            (
                transfer_no,
                payload.vehicle_id,
                vehicle["plate_no"],
                vehicle["carrier_id"],
                payload.to_carrier_id,
                payload.reason,
                admin_id,
                now,
            ),
        )
        transfer_id = cursor.lastrowid
        # 只更新车辆主数据归属，历史任务中的车辆引用与快照保持不变
        conn.execute(
            "UPDATE vehicles SET carrier_id = ?, updated_at = ? WHERE id = ?",
            (payload.to_carrier_id, now, payload.vehicle_id),
        )
        notice = f"车辆 {vehicle['plate_no']} 已转籍至新物流公司。原因：{payload.reason}"
        _notify(conn, vehicle["carrier_id"], "车辆转籍结果", "车辆转籍结果", notice, transfer_id, now)
        _notify(conn, payload.to_carrier_id, "车辆转籍结果", "车辆转籍结果", notice, transfer_id, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    row = conn.execute(_TRANSFER_SELECT + " WHERE id = ?", (transfer_id,)).fetchone()
    return _transfer_out(row)


def list_transfers(
    conn: sqlite3.Connection, vehicle_id: int | None = None
) -> list[VehicleTransferOut]:
    """列出转籍历史，可按车辆筛选。"""
    if vehicle_id is not None:
        rows = conn.execute(
            _TRANSFER_SELECT + " WHERE vehicle_id = ? ORDER BY id ASC", (vehicle_id,)
        ).fetchall()
    else:
        rows = conn.execute(_TRANSFER_SELECT + " ORDER BY id ASC").fetchall()
    return [_transfer_out(row) for row in rows]
