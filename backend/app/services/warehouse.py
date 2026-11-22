"""仓库主数据业务：列表、搜索、创建、修改与状态流转。"""

import sqlite3
from datetime import datetime, timezone

from app.exceptions import WarehouseNotFoundError
from app.schemas.warehouse import WarehouseIn, WarehouseOut

_WAREHOUSE_COLUMNS = (
    "id, shipper_id, name, contact, phone, province, city, district, "
    "detail_address, type, remarks, status, created_at, updated_at"
)


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符，保持用户的字面匹配语义。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _to_out(row: sqlite3.Row) -> WarehouseOut:
    """把仓库行组装成出参，位置由省市区与详细地址拼接。"""
    return WarehouseOut(
        id=row["id"],
        shipper_id=row["shipper_id"],
        name=row["name"],
        location=(
            f"{row['province']}{row['city']}{row['district']}{row['detail_address']}"
        ),
        contact=row["contact"],
        phone=row["phone"],
        province=row["province"],
        city=row["city"],
        district=row["district"],
        detail_address=row["detail_address"],
        type=row["type"],
        remarks=row["remarks"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_owned(
    conn: sqlite3.Connection, shipper_id: int, warehouse_id: int
) -> sqlite3.Row:
    """按当前货主读取仓库，非本人记录一律视为不存在。"""
    row = conn.execute(
        f"SELECT {_WAREHOUSE_COLUMNS} FROM warehouses "
        "WHERE id = ? AND shipper_id = ?",
        (warehouse_id, shipper_id),
    ).fetchone()
    if row is None:
        raise WarehouseNotFoundError()
    return row


def list_warehouses(
    conn: sqlite3.Connection,
    shipper_id: int,
    name: str | None = None,
    status: str | None = None,
) -> list[WarehouseOut]:
    """列出当前货主的仓库，可按名称模糊搜索与状态筛选。"""
    clauses = ["shipper_id = ?"]
    params: list[object] = [shipper_id]
    if name:
        clauses.append("name LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(name)}%")
    if status:
        clauses.append("status = ?")
        params.append(status)
    rows = conn.execute(
        f"SELECT {_WAREHOUSE_COLUMNS} FROM warehouses WHERE "
        + " AND ".join(clauses)
        + " ORDER BY id DESC",
        params,
    ).fetchall()
    return [_to_out(row) for row in rows]


def create_warehouse(
    conn: sqlite3.Connection, shipper_id: int, data: WarehouseIn
) -> WarehouseOut:
    """为当前货主新增一个正常状态的仓库。"""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        cursor = conn.execute(
            """INSERT INTO warehouses
               (shipper_id, name, contact, phone, province, city, district,
                detail_address, type, remarks, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '正常', ?, ?)""",
            (
                shipper_id,
                data.name,
                data.contact,
                data.phone,
                data.province,
                data.city,
                data.district,
                data.detail_address,
                data.type,
                data.remarks,
                now,
                now,
            ),
        )
        conn.commit()
        warehouse_id = cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    return _to_out(_get_owned(conn, shipper_id, warehouse_id))


def update_warehouse(
    conn: sqlite3.Connection, shipper_id: int, warehouse_id: int, data: WarehouseIn
) -> WarehouseOut:
    """修改当前货主仓库的主数据，不影响状态与既有订单。"""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        _get_owned(conn, shipper_id, warehouse_id)
        conn.execute(
            """UPDATE warehouses SET name = ?, contact = ?, phone = ?,
               province = ?, city = ?, district = ?, detail_address = ?,
               type = ?, remarks = ?, updated_at = ?
               WHERE id = ? AND shipper_id = ?""",
            (
                data.name,
                data.contact,
                data.phone,
                data.province,
                data.city,
                data.district,
                data.detail_address,
                data.type,
                data.remarks,
                now,
                warehouse_id,
                shipper_id,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _to_out(_get_owned(conn, shipper_id, warehouse_id))


def set_warehouse_status(
    conn: sqlite3.Connection, shipper_id: int, warehouse_id: int, status: str
) -> WarehouseOut:
    """启用或停用仓库；停用仅改状态，不物理删除、不回写历史订单。"""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("BEGIN IMMEDIATE")
    try:
        _get_owned(conn, shipper_id, warehouse_id)
        conn.execute(
            "UPDATE warehouses SET status = ?, updated_at = ? "
            "WHERE id = ? AND shipper_id = ?",
            (status, now, warehouse_id, shipper_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _to_out(_get_owned(conn, shipper_id, warehouse_id))
