"""分端会话 cookie 隔离的回归测试。"""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

PASSWORD = "test-pass-123"


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "isolation.db"),
        data_dir=str(tmp_path / "data"),
        cookie_secure=False,
        seed_admin_phone="13800138000",
        seed_admin_password=PASSWORD,
        seed_dev_accounts=True,
        dev_password=PASSWORD,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def login(client: TestClient, phone: str, client_id: str | None = None):
    headers = {"X-Client-Id": client_id} if client_id else {}
    return client.post(
        "/api/auth/login",
        json={"phone": phone, "password": PASSWORD},
        headers=headers,
    )


def test_two_clients_keep_separate_sessions(client: TestClient):
    """同域下两端各存各的 cookie，/me 按端返回对应角色。"""
    assert login(client, "13800138000").status_code == 200
    assert login(client, "13800138002", "h5").status_code == 200

    assert client.cookies.get("session_token")
    assert client.cookies.get("h5_session_token")

    assert client.get("/api/auth/me").json()["role"] == "管理员"
    assert client.get("/api/auth/me", headers={"X-Client-Id": "h5"}).json()["role"] == "司机"


def test_h5_login_does_not_overwrite_web_cookie(client: TestClient):
    """H5 登录不得覆盖 Web 的会话 cookie。"""
    assert login(client, "13800138000").status_code == 200
    web_cookie = client.cookies.get("session_token")

    assert login(client, "13800138002", "h5").status_code == 200

    assert client.cookies.get("session_token") == web_cookie


def test_h5_logout_only_clears_h5_cookie(client: TestClient):
    """H5 退出按端读 CSRF 与 cookie，不影响 Web 会话。"""
    assert login(client, "13800138000").status_code == 200
    web_cookie = client.cookies.get("session_token")
    h5_login = login(client, "13800138002", "h5")
    h5_csrf = h5_login.json()["csrf_token"]

    resp = client.post(
        "/api/auth/logout",
        headers={"X-Client-Id": "h5", "X-CSRF-Token": h5_csrf},
    )
    assert resp.status_code == 204
    assert client.cookies.get("h5_session_token") is None
    assert client.cookies.get("session_token") == web_cookie
    assert client.get("/api/auth/me").json()["role"] == "管理员"


def test_h5_session_not_visible_without_header(client: TestClient):
    """不带端标识时只认 Web cookie，不会读到 H5 会话。"""
    assert login(client, "13800138002", "h5").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
