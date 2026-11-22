"""站内通知写入的唯一实现：各业务域通过别名复用，保持行为一致。"""

import sqlite3


def notify(
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
