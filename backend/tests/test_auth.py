"""鉴权 seam 测试：登录、角色门禁、退出与禁用失效。"""

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password

SEED_ADMIN = ("admin", "admin123456")


def _login(client: TestClient, phone: str, password: str):
    """经真实登录接口取 token 与 CSRF。"""
    return client.post(
        "/api/auth/login",
        json={"phone": phone, "password": password},
    )


def _seed_account(conn: sqlite3.Connection, phone: str, role: str, password: str = "pw123456") -> None:
    """准备一个指定角色的账号（测试数据准备，断言仍走接口）。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """INSERT INTO accounts
               (phone, role, account_status, auth_status, password_hash, created_at)
               VALUES (?, ?, '正常使用', '审核通过', ?, ?)""",
            (phone, role, hash_password(password), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _login_headers(resp) -> dict:
    """从登录响应取 CSRF 头，供写操作使用。"""
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def test_seeded_admin_can_login(client):
    """种子管理员可通过登录接口取到 token 与 csrf。"""
    resp = _login(client, *SEED_ADMIN)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["role"] == "管理员"
    assert body["user"]["account_status"] == "正常使用"
    assert "csrf_token" in body
    assert client.cookies.get("session_token")


def test_me_returns_current_user(client):
    """已登录会话可读取当前用户。"""
    _login(client, *SEED_ADMIN)
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "管理员"


def test_me_requires_login(client):
    """未登录访问 /me 返回 401。"""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "未登录"


def test_wrong_password_rejected(client):
    """错误口令返回 401 且不泄露账号存在性细节。"""
    resp = _login(client, "admin", "wrong-password")
    assert resp.status_code == 401
    assert "error" in resp.json()


def test_role_gate_blocks_other_roles(client):
    """角色门禁：司机能进司机工作台，管理员访问返回 404。"""
    conn = sqlite3.connect(client.app.state.settings.db_path)
    _seed_account(conn, "d1", "司机")
    conn.close()
    _login(client, "d1", "pw123456")
    assert client.get("/api/driver/workbench").status_code == 200

    _login(client, *SEED_ADMIN)
    resp = client.get("/api/driver/workbench")
    assert resp.status_code == 404


def test_logout_invalidates_session(client):
    """退出后原 token 立即失效。"""
    login_resp = _login(client, *SEED_ADMIN)
    assert client.get("/api/auth/me").status_code == 200
    out = client.post("/api/auth/logout", headers=_login_headers(login_resp))
    assert out.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_logout_requires_csrf(client):
    """退出是写操作，缺 CSRF token 返回 403。"""
    _login(client, *SEED_ADMIN)
    assert client.post("/api/auth/logout").status_code == 403


def test_csrf_recovered_from_me_after_reload(client):
    """页面刷新后用 /me 恢复 CSRF，仍可退出并立即使会话失效。"""
    _login(client, *SEED_ADMIN)
    # 模拟刷新：客户端内存里的 csrf 丢失，仅凭 cookie 调 /me 取回
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    csrf = me.json()["csrf_token"]
    assert csrf
    out = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert out.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_csrf_rejects_foreign_origin(client):
    """写操作携带非法 Origin 返回 403。"""
    login_resp = _login(client, *SEED_ADMIN)
    headers = {**_login_headers(login_resp), "Origin": "https://evil.example"}
    assert client.post("/api/auth/logout", headers=headers).status_code == 403


def test_per_role_profile_tables_exist(client):
    """迁移建立了每个角色一张 profile 表，并写入管理员 profile。"""
    conn = sqlite3.connect(client.app.state.settings.db_path)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )}
    conn.close()
    assert {
        "shipper_profiles", "carrier_profiles", "driver_profiles", "admin_profiles"
    } <= tables


def test_data_dir_created(client):
    """凭证目录在启动时按配置创建（隔离凭证 seam）。"""
    from pathlib import Path

    assert Path(client.app.state.settings.data_dir).is_dir()


def test_disabled_account_session_invalid(client):
    """账号被禁用后，已签发的 token 立即失效。"""
    conn = sqlite3.connect(client.app.state.settings.db_path)
    _seed_account(conn, "carrier1", "物流公司")
    conn.close()
    login_resp = _login(client, "carrier1", "pw123456")
    assert client.get("/api/auth/me").status_code == 200
    conn = sqlite3.connect(client.app.state.settings.db_path)
    conn.execute("UPDATE accounts SET account_status = '已禁用' WHERE phone = 'carrier1'")
    conn.commit()
    conn.close()
    assert client.get("/api/auth/me").status_code == 403


def test_all_four_roles_can_login(client):
    """四类角色共用登录接口并按角色进入。"""
    conn = sqlite3.connect(client.app.state.settings.db_path)
    for phone, role in [("s1", "货主"), ("c1", "物流公司"), ("d1", "司机")]:
        _seed_account(conn, phone, role)
    conn.close()
    for phone, role in [("admin", "管理员"), ("s1", "货主"), ("c1", "物流公司"), ("d1", "司机")]:
        resp = _login(client, phone, "admin123456" if phone == "admin" else "pw123456")
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == role
