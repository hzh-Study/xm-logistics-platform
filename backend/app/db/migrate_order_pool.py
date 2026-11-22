"""订单池与承接迁移（v6）：在 orders 上追加承接归属列并建筛选索引。"""

import sqlite3

# orders 是可变业务实体，只做追加列；承接仅写状态与归属，不触碰收发快照。
_ORDER_POOL_COLUMNS = [
    (
        "carrier_id",
        "ALTER TABLE orders ADD COLUMN carrier_id INTEGER "
        "REFERENCES accounts(id) ON DELETE RESTRICT",  # 承接物流公司账号 id，待承接时为空
    ),
    ("accepted_at", "ALTER TABLE orders ADD COLUMN accepted_at TEXT"),  # 承接时间，ISO 8601
]

_ORDER_POOL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at, id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_carrier_status ON orders(carrier_id, status, id)",
]


def migrate_order_pool(conn: sqlite3.Connection) -> None:
    """在已开启的事务内幂等追加订单池字段与索引。"""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    for name, statement in _ORDER_POOL_COLUMNS:
        if name not in existing:
            conn.execute(statement)
    for statement in _ORDER_POOL_INDEXES:
        conn.execute(statement)
