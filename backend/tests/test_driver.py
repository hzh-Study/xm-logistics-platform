"""司机创建与身份绑定 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。"""

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password

TEMP_PASSWORD = "temp123456"
NEW_PASSWORD = "new123456"
CARRIER_PASSWORD = "pw123456"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path(client: TestClient) -> str:
    return client.app.state.settings.db_path


def _seed_carrier(
    client: TestClient,
    phone: str = "carrier1",
    *,
    account_status: str = "正常使用",
    auth_status: str = "审核通过",
) -> int:
    """准备一个物流公司账号（仅数据准备，不用于断言）。"""
    conn = sqlite3.connect(_db_path(client))
    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            """INSERT INTO accounts
               (phone, role, account_status, auth_status, password_hash, created_at)
               VALUES (?, '物流公司', ?, ?, ?, ?)""",
            (phone, account_status, auth_status, hash_password(CARRIER_PASSWORD), _now()),
        )
        account_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO carrier_profiles (account_id, company_name, license_no) VALUES (?, ?, '')",
            (account_id, "顺达物流"),
        )
        conn.commit()
        return account_id
    finally:
        conn.close()


def _login(client: TestClient, phone: str, password: str):
    return client.post("/api/auth/login", json={"phone": phone, "password": password})


def _csrf(resp) -> dict:
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _carrier_login(client: TestClient, phone: str = "carrier1") -> dict:
    return _csrf(_login(client, phone, CARRIER_PASSWORD))


def _create_driver(
    client: TestClient, carrier_csrf: dict, phone: str, name: str = "张三"
):
    return client.post(
        "/api/carrier/drivers",
        headers=carrier_csrf,
        json={"phone": phone, "password": TEMP_PASSWORD, "name": name},
    )


def _onboard_driver(client: TestClient, phone: str) -> dict:
    """用司机的真实会话完成改密与身份绑定，返回司机 CSRF 头。"""
    login = _login(client, phone, TEMP_PASSWORD)
    assert login.status_code == 200
    headers = _csrf(login)
    assert (
        client.post(
            "/api/driver/change-password",
            headers=headers,
            json={"new_password": NEW_PASSWORD},
        ).status_code
        == 204
    )
    binding = client.post(
        "/api/driver/binding",
        headers=headers,
        json={
            "name": "张三",
            "id_number": "110101199001011234",
            "license_no": "LIC-2026-001",
            "license_type": "B2",
            "license_expiry": "2030-01-01",
        },
    )
    assert binding.status_code == 200
    return headers


BINDING_PAYLOAD = {
    "name": "张三",
    "id_number": "110101199001011234",
    "license_no": "LIC-2026-001",
    "license_type": "B2",
    "license_expiry": "2030-01-01",
}


# 1. 公司创建司机并归属本公司
def test_carrier_creates_driver_owned_by_company(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    resp = _create_driver(client, csrf, "driver-a")
    assert resp.status_code == 201
    body = resp.json()
    assert body["phone"] == "driver-a"
    assert body["name"] == "张三"
    assert body["auth_status"] == "未提交"
    assert body["availability"] == "可派单"
    assert body["employment"] == "在职"
    assert body["account_status"] == "正常使用"
    assert body["binding_complete"] is False
    assert body["must_change_password"] is True

    listed = client.get("/api/carrier/drivers")
    assert listed.status_code == 200
    assert [row["phone"] for row in listed.json()] == ["driver-a"]


# 2. 首次登录强制改密 + 身份绑定后才可进入工作台
def test_first_login_forced_flow_then_workspace(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    created = _create_driver(client, csrf, "driver-b")
    assert created.status_code == 201
    account_id = created.json()["account_id"]

    login = _login(client, "driver-b", TEMP_PASSWORD)
    assert login.status_code == 200
    headers = _csrf(login)

    onboarding = client.get("/api/driver/onboarding").json()
    assert onboarding["must_change_password"] is True
    assert onboarding["binding_complete"] is False
    assert onboarding["company_name"] == "顺达物流"

    # 未完成前不能进入工作台，也不能跳过改密直接绑定
    assert client.get("/api/driver/workspace").status_code == 403
    assert (
        client.post("/api/driver/binding", headers=headers, json=BINDING_PAYLOAD).status_code
        == 403
    )

    assert (
        client.post(
            "/api/driver/change-password",
            headers=headers,
            json={"new_password": NEW_PASSWORD},
        ).status_code
        == 204
    )
    # 已改密但未绑定仍被拦截
    assert client.get("/api/driver/workspace").status_code == 403

    binding = client.post("/api/driver/binding", headers=headers, json=BINDING_PAYLOAD)
    assert binding.status_code == 200
    assert binding.json()["binding_complete"] is True

    onboarding = client.get("/api/driver/onboarding").json()
    assert onboarding["must_change_password"] is False
    assert onboarding["binding_complete"] is True

    workspace = client.get("/api/driver/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["name"] == "张三"
    assert workspace.json()["company_name"] == "顺达物流"

    # 临时口令立即失效
    assert _login(client, "driver-b", TEMP_PASSWORD).status_code == 401
    assert _login(client, "driver-b", NEW_PASSWORD).status_code == 200

    # 公司看到认证状态进入待审核与驾驶资格
    csrf = _carrier_login(client)
    detail = client.get(f"/api/carrier/drivers/{account_id}")
    assert detail.json()["auth_status"] == "待审核"
    assert detail.json()["license_type"] == "B2"
    assert detail.json()["license_no"] == "LIC-2026-001"


# 3. 三类状态互不合并、互相独立
def test_three_independent_status_dimensions(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    created = _create_driver(client, csrf, "driver-c")
    account_id = created.json()["account_id"]
    _onboard_driver(client, "driver-c")
    csrf = _carrier_login(client)

    paused = client.post(
        f"/api/carrier/drivers/{account_id}/availability",
        headers=csrf,
        json={"availability": "暂停接单"},
    )
    assert paused.status_code == 200
    row = paused.json()
    assert row["availability"] == "暂停接单"
    assert row["employment"] == "在职"
    assert row["account_status"] == "正常使用"
    assert row["can_dispatch_new"] is False
    assert row["can_continue_in_flight"] is True

    departed = client.post(
        f"/api/carrier/drivers/{account_id}/employment",
        headers=csrf,
        json={"employment": "离职"},
    )
    assert departed.status_code == 200
    row = departed.json()
    assert row["availability"] == "暂停接单"
    assert row["employment"] == "离职"
    assert row["account_status"] == "已禁用"
    assert row["departure_date"] is not None
    assert row["can_continue_in_flight"] is False

    restored = client.post(
        f"/api/carrier/drivers/{account_id}/account-status",
        headers=csrf,
        json={"account_status": "正常使用"},
    )
    assert restored.status_code == 200
    row = restored.json()
    assert row["employment"] == "离职"
    assert row["availability"] == "暂停接单"
    assert row["account_status"] == "正常使用"


# 4. 暂停接单不阻断在途打卡签收：工作台仍可进入
def test_paused_driver_still_enters_workspace(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    created = _create_driver(client, csrf, "driver-d")
    account_id = created.json()["account_id"]
    _onboard_driver(client, "driver-d")

    csrf = _carrier_login(client)
    client.post(
        f"/api/carrier/drivers/{account_id}/availability",
        headers=csrf,
        json={"availability": "暂停接单"},
    )
    assert _login(client, "driver-d", NEW_PASSWORD).status_code == 200
    workspace = client.get("/api/driver/workspace")
    assert workspace.status_code == 200
    # 司机端不应看到运费报价字段
    assert "freight_quote" not in workspace.json()


# 5. 所属公司异常 / 未绑定 / 离职时阻断
def test_driver_blocked_when_unbound_company_disabled_or_departed(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    created = _create_driver(client, csrf, "driver-e")
    account_id = created.json()["account_id"]
    _onboard_driver(client, "driver-e")

    # 所属物流公司账号被禁用
    conn = sqlite3.connect(_db_path(client))
    conn.execute("UPDATE accounts SET account_status = '已禁用' WHERE role = '物流公司'")
    conn.commit()
    conn.close()
    blocked = client.get("/api/driver/workspace")
    assert blocked.status_code == 403
    assert "物流公司" in blocked.json()["error"]["message"]

    # 未绑定物流公司的司机（无 profile 行）
    conn = sqlite3.connect(_db_path(client))
    conn.execute(
        """INSERT INTO accounts
           (phone, role, account_status, auth_status, password_hash, created_at)
           VALUES ('orphan', '司机', '正常使用', '审核通过', ?, ?)""",
        (hash_password(TEMP_PASSWORD), _now()),
    )
    conn.commit()
    conn.close()
    assert _login(client, "orphan", TEMP_PASSWORD).status_code == 200
    assert client.get("/api/driver/workspace").status_code == 403


# 6. 司机不能自行注册或进入公共订单池
def test_driver_cannot_self_register_or_reach_order_pool(client):
    assert client.post("/api/auth/register", json={}).status_code == 404
    assert client.post("/api/driver/register", json={}).status_code == 404

    _seed_carrier(client)
    csrf = _carrier_login(client)
    _create_driver(client, csrf, "driver-f")
    _onboard_driver(client, "driver-f")

    assert client.get("/api/carrier/business-access").status_code == 404
    assert client.get("/api/carrier/drivers").status_code == 404
    assert client.get("/api/carrier/orders/pool").status_code == 404


# 7. 物流公司之间的司机数据隔离
def test_carrier_permission_isolation(client):
    _seed_carrier(client, "carrier-a")
    _seed_carrier(client, "carrier-b")
    csrf_a = _carrier_login(client, "carrier-a")
    resp_a = _create_driver(client, csrf_a, "driver-ga")
    id_a = resp_a.json()["account_id"]

    csrf_b = _carrier_login(client, "carrier-b")
    _create_driver(client, csrf_b, "driver-gb")
    listed_b = client.get("/api/carrier/drivers").json()
    assert [row["phone"] for row in listed_b] == ["driver-gb"]
    assert client.get(f"/api/carrier/drivers/{id_a}").status_code == 404
    assert (
        client.put(
            f"/api/carrier/drivers/{id_a}",
            headers=csrf_b,
            json={"name": "篡改"},
        ).status_code
        == 404
    )


# 8. 身份资料历史只读追加；重要身份变更触发重新审核
def test_identity_history_append_only_and_reverification(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    created = _create_driver(client, csrf, "driver-h")
    account_id = created.json()["account_id"]
    _onboard_driver(client, "driver-h")
    csrf = _carrier_login(client)

    history = client.get(f"/api/carrier/drivers/{account_id}/identity-history").json()
    assert len(history) == 1
    assert history[0]["reason"] == "首次身份绑定"
    assert history[0]["actor"] == "司机"
    first_id = history[0]["id"]

    changed = client.put(
        f"/api/carrier/drivers/{account_id}",
        headers=csrf,
        json={"name": "张三", "id_number": "110101199001019999"},
    )
    assert changed.status_code == 200
    assert changed.json()["auth_status"] == "待审核"
    history = client.get(f"/api/carrier/drivers/{account_id}/identity-history").json()
    assert len(history) == 2
    assert history[1]["replaced_by"] == first_id
    assert history[1]["reason"] == "身份资料变更"
    assert history[0]["id_number"] == "110101199001011234"

    # 仅修改姓名属基本资料，不触发重新审核、不追加身份历史
    conn = sqlite3.connect(_db_path(client))
    conn.execute(
        "UPDATE accounts SET auth_status = '审核通过' WHERE id = ?", (account_id,)
    )
    conn.commit()
    conn.close()
    renamed = client.put(
        f"/api/carrier/drivers/{account_id}", headers=csrf, json={"name": "李四"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["auth_status"] == "审核通过"
    assert renamed.json()["name"] == "李四"
    assert len(client.get(f"/api/carrier/drivers/{account_id}/identity-history").json()) == 2


# 9. 手机号重复被拒绝
def test_duplicate_driver_phone_rejected(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    assert _create_driver(client, csrf, "driver-i").status_code == 201
    assert _create_driver(client, csrf, "driver-i").status_code == 409


# 10. 其他角色访问司机管理接口返回 404
def test_other_roles_cannot_access_driver_management(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    _create_driver(client, csrf, "driver-j")

    assert _login(client, "admin", "admin123456").status_code == 200
    assert client.get("/api/carrier/drivers").status_code == 404
