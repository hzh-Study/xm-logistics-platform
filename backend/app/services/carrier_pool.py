"""物流公司订单池业务：货源浏览、筛选、详情与先到先得承接。"""

import sqlite3
from datetime import datetime
from decimal import Decimal

from app.exceptions import OrderNotAcceptableError, PoolOrderNotFoundError
from app.schemas.shipper import OrderOut
from app.services.shipper import ORDER_COLUMNS, to_order_out

_POOL_STATUS = "待承接"


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符，保持用户的字面匹配语义。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _yuan_to_cents(value: str) -> int:
    """API 边界的元字符串转换为库内整数分。"""
    return int(Decimal(value) * 100)


def list_pool(
    conn: sqlite3.Connection,
    shipping_place: str | None = None,
    receiving_place: str | None = None,
    cargo_type: str | None = None,
    vehicle_type: str | None = None,
    weight: str | None = None,
    published_from: str | None = None,
    published_to: str | None = None,
    quote_min_yuan: str | None = None,
    quote_max_yuan: str | None = None,
) -> list[OrderOut]:
    """列出公共池中全部待承接货源，按发货地 / 收货地 / 类型 / 重量 / 时间 / 运费筛选。"""
    clauses = ["status = ?"]
    params: list[object] = [_POOL_STATUS]
    if shipping_place:
        clauses.append(
            "(ship_detail_address LIKE ? ESCAPE '\\' OR ship_city LIKE ? ESCAPE '\\')"
        )
        escaped = f"%{_escape_like(shipping_place)}%"
        params.extend([escaped, escaped])
    if receiving_place:
        clauses.append(
            "(recv_detail_address LIKE ? ESCAPE '\\' OR recv_city LIKE ? ESCAPE '\\')"
        )
        escaped = f"%{_escape_like(receiving_place)}%"
        params.extend([escaped, escaped])
    if cargo_type:
        clauses.append("cargo_type LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(cargo_type)}%")
    if vehicle_type:
        clauses.append("vehicle_type LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(vehicle_type)}%")
    if weight:
        clauses.append("weight LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(weight)}%")
    if published_from:
        clauses.append("created_at >= ?")
        params.append(published_from)
    if published_to:
        clauses.append("created_at <= ?")
        params.append(published_to)
    if quote_min_yuan:
        clauses.append("quote_amount_cents >= ?")
        params.append(_yuan_to_cents(quote_min_yuan))
    if quote_max_yuan:
        clauses.append("quote_amount_cents <= ?")
        params.append(_yuan_to_cents(quote_max_yuan))
    rows = conn.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders WHERE "
        + " AND ".join(clauses)
        + " ORDER BY id DESC",
        params,
    ).fetchall()
    return [to_order_out(row) for row in rows]


def get_pool_detail(conn: sqlite3.Connection, order_id: int) -> OrderOut:
    """读取公共池中一条待承接货源的完整详情。"""
    row = conn.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders WHERE id = ? AND status = ?",
        (order_id, _POOL_STATUS),
    ).fetchone()
    if row is None:
        raise PoolOrderNotFoundError()
    return to_order_out(row)


def _get_order(conn: sqlite3.Connection, order_id: int) -> sqlite3.Row:
    """按 id 读取任意状态订单，供承接后回读结果。"""
    row = conn.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        raise PoolOrderNotFoundError()
    return row


def accept_order(
    conn: sqlite3.Connection, order_id: int, carrier_id: int
) -> OrderOut:
    """先到先得承接：唯一归属当前物流公司，移出公共池并给货主落通知。"""
    now = datetime.now().isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        order = conn.execute(
            "SELECT shipper_id, order_no, status FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if order is None:
            raise PoolOrderNotFoundError()
        if order["status"] != _POOL_STATUS:
            raise OrderNotAcceptableError()
        updated = conn.execute(
            """UPDATE orders SET status = '已承接', carrier_id = ?, accepted_at = ?
               WHERE id = ? AND status = ?""",
            (carrier_id, now, order_id, _POOL_STATUS),
        )
        if updated.rowcount != 1:
            raise OrderNotAcceptableError()
        conn.execute(
            """INSERT INTO notifications
               (recipient_id, recipient_role, kind, title, body, related_id, created_at)
               VALUES (?, '货主', '订单已被承接', '运输订单已被承接', ?, ?, ?)""",
            (
                order["shipper_id"],
                f"您的运输订单 {order['order_no']} 已被物流公司承接。",
                order_id,
                now,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return to_order_out(_get_order(conn, order_id))
