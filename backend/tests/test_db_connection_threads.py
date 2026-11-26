"""SQLite 连接跨线程使用的回归测试。"""

from concurrent.futures import ThreadPoolExecutor

from app.db.connection import connect


def test_connection_survives_cross_thread_use(tmp_path):
    """FastAPI 同步依赖跨线程 yield/close，连接须允许跨线程使用。"""
    with ThreadPoolExecutor(max_workers=1) as pool:
        conn = pool.submit(connect, str(tmp_path / "thread.db")).result()

    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")

    with ThreadPoolExecutor(max_workers=1) as pool:
        rows = pool.submit(lambda: conn.execute("SELECT 1 AS id").fetchall()).result()
    assert rows[0]["id"] == 1

    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(conn.close).result()
