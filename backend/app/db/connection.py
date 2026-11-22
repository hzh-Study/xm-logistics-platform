"""SQLite 连接工厂：每连接设 pragma，按请求创建与关闭。"""

import sqlite3
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    """打开连接并应用连接级 pragma；事务由调用方显式 BEGIN 管理。"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    # 显式事务模式：autocommit=False 会让连接常驻事务，导致 PRAGMA 无法设置
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = FULL")
    return conn


def initialize(db_path: str) -> None:
    """初始化库：设置持久 pragma 并执行迁移。"""
    conn = connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        from app.db.migrate import migrate

        migrate(conn)
    finally:
        conn.close()
