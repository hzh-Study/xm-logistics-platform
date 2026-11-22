"""HTTP 黑盒 seam：每例独立临时库 + 隔离凭证目录，经真实接口驱动。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """构造带临时库与隔离凭证目录的应用客户端。"""
    # TestClient 走 http，关闭 Secure 以便回传 cookie
    settings = Settings(
        db_path=str(tmp_path / "test.db"),
        data_dir=str(tmp_path / "data"),
        cookie_secure=False,
        seed_admin_phone="admin",
        seed_admin_password="admin123456",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client
