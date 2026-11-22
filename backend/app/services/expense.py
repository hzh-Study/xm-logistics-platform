"""报销费用业务：按已完成运输任务提交、公司筛选审核、线下支付标记与驳回重提。"""

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

from app.exceptions import ExpenseNotFoundError, ExpenseRuleError, TaskStateError
from app.schemas.expense import ExpenseIn, ExpenseOut, ExpenseReviewIn
from app.services import checkin as checkin_service


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cents_to_yuan(cents: int) -> str:
    """金额从整数分转为元字符串，仅在出参边界转换。"""
    return f"{cents // 100}.{cents % 100:02d}"


def _expense_no(conn: sqlite3.Connection, now: str) -> str:
    """按天生成报销费用编号，FE-YYMMDD-0001，单事务内不重号。"""
    prefix = f"FE-{datetime.fromisoformat(now).strftime('%y%m%d')}"
    used = conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE expense_no LIKE ?", (f"{prefix}-%",)
    ).fetchone()[0]
    return f"{prefix}-{used + 1:04d}"


def _expense(conn: sqlite3.Connection, expense_id: int):
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    if row is None:
        raise ExpenseNotFoundError()
    return row


def _expense_out(conn: sqlite3.Connection, row) -> ExpenseOut:
    """把费用行与追加式审核 / 支付事件汇总为出参，两条状态独立。"""
    expense_id = row["id"]
    vouchers = [
        item["path"]
        for item in conn.execute(
            "SELECT path FROM expense_vouchers WHERE expense_id = ? ORDER BY id ASC", (expense_id,)
        )
    ]
    review = conn.execute(
        """SELECT event, reason, actor_id, created_at FROM expense_history
           WHERE expense_id = ? AND event IN ('审核通过','审核驳回')
           ORDER BY id DESC LIMIT 1""",
        (expense_id,),
    ).fetchone()
    payment = conn.execute(
        """SELECT actor_id, created_at FROM expense_history
           WHERE expense_id = ? AND event = '标记已支付' ORDER BY id DESC LIMIT 1""",
        (expense_id,),
    ).fetchone()
    task_no = conn.execute(
        "SELECT task_no FROM transport_tasks WHERE id = ?", (row["task_id"],)
    ).fetchone()["task_no"]
    driver_name = conn.execute(
        "SELECT name FROM driver_profiles WHERE account_id = ?", (row["driver_account_id"],)
    ).fetchone()
    successor = conn.execute(
        "SELECT id FROM expenses WHERE replaced_by = ? LIMIT 1", (expense_id,)
    ).fetchone()
    return ExpenseOut(
        id=expense_id,
        expense_no=row["expense_no"],
        task_id=row["task_id"],
        task_no=task_no,
        order_id=row["order_id"],
        driver_account_id=row["driver_account_id"],
        driver_name=driver_name["name"] if driver_name else "",
        carrier_account_id=row["carrier_account_id"],
        expense_type=row["expense_type"],
        amount_yuan=_cents_to_yuan(row["amount_cents"]),
        incurred_at=row["incurred_at"],
        description=row["description"],
        vouchers=vouchers,
        review_status=review["event"] if review else "待审核",
        review_reason=review["reason"] if review else "",
        payment_status="已支付" if payment else "待支付",
        reviewed_at=review["created_at"] if review else None,
        reviewed_by_account_id=review["actor_id"] if review else None,
        paid_at=payment["created_at"] if payment else None,
        paid_by_account_id=payment["actor_id"] if payment else None,
        replaced_by=row["replaced_by"],
        superseded_by=successor["id"] if successor else None,
        created_at=row["created_at"],
    )


def submit_expense(
    conn: sqlite3.Connection, driver_id: int, task_id: int, payload: ExpenseIn
) -> ExpenseOut:
    """司机按已完成且属于自己的运输任务单笔提交报销费用。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        task = checkin_service._driver_task(conn, driver_id, task_id)
        if task["status"] != "已完成":
            raise TaskStateError("运输任务须为已完成状态才可提交报销费用")
        expense_no = _expense_no(conn, now)
        cursor = conn.execute(
            """INSERT INTO expenses
               (expense_no, task_id, order_id, driver_account_id, carrier_account_id,
                expense_type, amount_cents, incurred_at, description, replaced_by,
                actor, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, '司机', ?)""",
            (
                expense_no,
                task_id,
                task["order_id"],
                driver_id,
                task["carrier_id"],
                payload.expense_type,
                int(Decimal(payload.amount_yuan) * 100),
                payload.incurred_at,
                payload.description,
                now,
            ),
        )
        expense_id = cursor.lastrowid
        for path in payload.vouchers:
            conn.execute(
                """INSERT INTO expense_vouchers (expense_id, path, actor, replaced_by, created_at)
                   VALUES (?, ?, '司机', NULL, ?)""",
                (expense_id, path, now),
            )
        conn.execute(
            """INSERT INTO expense_history
               (expense_id, event, reason, actor, actor_id, replaced_by, created_at)
               VALUES (?, '提交', '', '司机', ?, NULL, ?)""",
            (expense_id, driver_id, now),
        )
        body = (
            f"运输任务 {task['task_no']} 司机提交一笔{payload.expense_type}报销费用 "
            f"{payload.amount_yuan} 元，请审核。"
        )
        checkin_service._notify(
            conn, task["carrier_id"], "物流公司", "费用提交", "费用提交", body, expense_id, now
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _expense_out(conn, _expense(conn, expense_id))


def list_driver_expenses(conn: sqlite3.Connection, driver_id: int) -> list[ExpenseOut]:
    """司机查看自己提交的全部报销费用（含被驳回的历史记录）。"""
    rows = conn.execute(
        "SELECT * FROM expenses WHERE driver_account_id = ? ORDER BY created_at DESC, id DESC",
        (driver_id,),
    ).fetchall()
    return [_expense_out(conn, row) for row in rows]


def get_driver_expense(conn: sqlite3.Connection, driver_id: int, expense_id: int) -> ExpenseOut:
    """司机读取本人一笔报销费用；他人费用视为不存在。"""
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ? AND driver_account_id = ?", (expense_id, driver_id)
    ).fetchone()
    if row is None:
        raise ExpenseNotFoundError()
    return _expense_out(conn, row)


def list_carrier_expenses(
    conn: sqlite3.Connection,
    carrier_id: int,
    *,
    driver_account_id: int | None = None,
    task_id: int | None = None,
    expense_type: str | None = None,
    submitted_from: str | None = None,
    submitted_to: str | None = None,
    review_status: str | None = None,
    payment_status: str | None = None,
) -> list[ExpenseOut]:
    """物流公司按司机 / 任务 / 类型 / 提交时间 / 审核状态筛选本公司费用。"""
    sql = "SELECT e.* FROM expenses e WHERE e.carrier_account_id = ?"
    params: list[object] = [carrier_id]
    if driver_account_id is not None:
        sql += " AND e.driver_account_id = ?"
        params.append(driver_account_id)
    if task_id is not None:
        sql += " AND e.task_id = ?"
        params.append(task_id)
    if expense_type is not None:
        sql += " AND e.expense_type = ?"
        params.append(expense_type)
    if submitted_from is not None:
        sql += " AND e.created_at >= ?"
        params.append(submitted_from)
    if submitted_to is not None:
        sql += " AND e.created_at <= ?"
        params.append(submitted_to)
    if review_status is not None:
        sql += (
            " AND COALESCE((SELECT h.event FROM expense_history h "
            "WHERE h.expense_id = e.id AND h.event IN ('审核通过','审核驳回') "
            "ORDER BY h.id DESC LIMIT 1), '待审核') = ?"
        )
        params.append(review_status)
    if payment_status is not None:
        sql += (
            " AND EXISTS(SELECT 1 FROM expense_history p "
            "WHERE p.expense_id = e.id AND p.event = '标记已支付') = ?"
        )
        params.append(1 if payment_status == "已支付" else 0)
    sql += " ORDER BY e.created_at DESC, e.id DESC"
    rows = conn.execute(sql, params).fetchall()
    return [_expense_out(conn, row) for row in rows]


def get_carrier_expense(conn: sqlite3.Connection, carrier_id: int, expense_id: int) -> ExpenseOut:
    """物流公司读取本公司一笔报销费用；他公司费用视为不存在。"""
    row = conn.execute(
        "SELECT * FROM expenses WHERE id = ? AND carrier_account_id = ?", (expense_id, carrier_id)
    ).fetchone()
    if row is None:
        raise ExpenseNotFoundError()
    return _expense_out(conn, row)


def review_expense(
    conn: sqlite3.Connection, carrier_id: int, expense_id: int, payload: ExpenseReviewIn
) -> ExpenseOut:
    """物流公司审核本公司一笔费用；驳回原因必填，审核不影响支付状态。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _expense(conn, expense_id)
        if row["carrier_account_id"] != carrier_id:
            raise ExpenseNotFoundError()
        prior = conn.execute(
            """SELECT id FROM expense_history
               WHERE expense_id = ? AND event IN ('审核通过','审核驳回') LIMIT 1""",
            (expense_id,),
        ).fetchone()
        if prior is not None:
            raise ExpenseRuleError("该笔费用已审核，不可重复审核")
        if payload.decision == "审核驳回" and not payload.reason.strip():
            raise ExpenseRuleError("驳回原因必填")
        conn.execute(
            """INSERT INTO expense_history
               (expense_id, event, reason, actor, actor_id, replaced_by, created_at)
               VALUES (?, ?, ?, '物流公司', ?, NULL, ?)""",
            (expense_id, payload.decision, payload.reason, carrier_id, now),
        )
        approved = payload.decision == "审核通过"
        kind = "费用审核通过" if approved else "费用审核驳回"
        body = f"您提交的费用 {row['expense_no']} 审核{'通过' if approved else '驳回'}。"
        if not approved:
            body += f"驳回原因：{payload.reason}"
        checkin_service._notify(
            conn, row["driver_account_id"], "司机", kind, kind, body, expense_id, now
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _expense_out(conn, _expense(conn, expense_id))


def mark_paid(conn: sqlite3.Connection, carrier_id: int, expense_id: int) -> ExpenseOut:
    """线下付款后公司标记单笔费用已支付，追加操作人与时间。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _expense(conn, expense_id)
        if row["carrier_account_id"] != carrier_id:
            raise ExpenseNotFoundError()
        reviewed = conn.execute(
            """SELECT event FROM expense_history
               WHERE expense_id = ? AND event IN ('审核通过','审核驳回')
               ORDER BY id DESC LIMIT 1""",
            (expense_id,),
        ).fetchone()
        if reviewed is None or reviewed["event"] != "审核通过":
            raise ExpenseRuleError("费用审核通过后才可标记已支付")
        paid = conn.execute(
            "SELECT id FROM expense_history WHERE expense_id = ? AND event = '标记已支付' LIMIT 1",
            (expense_id,),
        ).fetchone()
        if paid is not None:
            raise ExpenseRuleError("该笔费用已标记已支付")
        conn.execute(
            """INSERT INTO expense_history
               (expense_id, event, reason, actor, actor_id, replaced_by, created_at)
               VALUES (?, '标记已支付', '', '物流公司', ?, NULL, ?)""",
            (expense_id, carrier_id, now),
        )
        body = f"您提交的费用 {row['expense_no']} 已由物流公司线下付款并标记已支付。"
        checkin_service._notify(
            conn, row["driver_account_id"], "司机", "费用已支付", "费用已支付", body,
            expense_id, now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _expense_out(conn, _expense(conn, expense_id))


def resubmit_expense(
    conn: sqlite3.Connection, driver_id: int, expense_id: int, payload: ExpenseIn
) -> ExpenseOut:
    """驳回后重新提交：生成新费用关联原笔，原笔作为历史保留。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        original = _expense(conn, expense_id)
        if original["driver_account_id"] != driver_id:
            raise ExpenseNotFoundError()
        review = conn.execute(
            """SELECT event FROM expense_history
               WHERE expense_id = ? AND event IN ('审核通过','审核驳回')
               ORDER BY id DESC LIMIT 1""",
            (expense_id,),
        ).fetchone()
        if review is None or review["event"] != "审核驳回":
            raise ExpenseRuleError("仅被驳回的费用可重新提交")
        successor = conn.execute(
            "SELECT id FROM expenses WHERE replaced_by = ? LIMIT 1", (expense_id,)
        ).fetchone()
        if successor is not None:
            raise ExpenseRuleError("该笔费用已重新提交")
        task = checkin_service._driver_task(conn, driver_id, original["task_id"])
        if task["status"] != "已完成":
            raise TaskStateError("运输任务须为已完成状态才可提交报销费用")

        expense_no = _expense_no(conn, now)
        cursor = conn.execute(
            """INSERT INTO expenses
               (expense_no, task_id, order_id, driver_account_id, carrier_account_id,
                expense_type, amount_cents, incurred_at, description, replaced_by,
                actor, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '司机', ?)""",
            (
                expense_no,
                original["task_id"],
                original["order_id"],
                driver_id,
                original["carrier_account_id"],
                payload.expense_type,
                int(Decimal(payload.amount_yuan) * 100),
                payload.incurred_at,
                payload.description,
                expense_id,
                now,
            ),
        )
        new_id = cursor.lastrowid
        for path in payload.vouchers:
            conn.execute(
                """INSERT INTO expense_vouchers (expense_id, path, actor, replaced_by, created_at)
                   VALUES (?, ?, '司机', NULL, ?)""",
                (new_id, path, now),
            )
        conn.execute(
            """INSERT INTO expense_history
               (expense_id, event, reason, actor, actor_id, replaced_by, created_at)
               VALUES (?, '重新提交', ?, '司机', ?, NULL, ?)""",
            (new_id, f"驳回重提，关联原笔 {original['expense_no']}", driver_id, now),
        )
        body = (
            f"运输任务 {task['task_no']} 司机已重新提交报销费用 {expense_no}，"
            f"关联被驳回的原笔 {original['expense_no']}，请审核。"
        )
        checkin_service._notify(
            conn, original["carrier_account_id"], "物流公司", "费用提交", "费用提交", body,
            new_id, now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _expense_out(conn, _expense(conn, new_id))
