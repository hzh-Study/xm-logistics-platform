"""车辆管理 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。"""

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password

CARRIER_PASSWORD = "pw123456"
DRIVER_PASSWORD = "temp123456"
NEW_PASSWORD = "new123456"


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


def _create_driver(client: TestClient, csrf: dict, phone: str, name: str = "张三") -> dict:
    resp = client.post(
        "/api/carrier/drivers",
        headers=csrf,
        json={"phone": phone, "password": DRIVER_PASSWORD, "name": name},
    )
    assert resp.status_code == 201
    return resp.json()


def _create_vehicle(
    client: TestClient,
    csrf: dict,
    plate_no: str = "京A12345",
    *,
    owner_type: str = "公司",
    owner_driver_id: int | None = None,
    document_status: str = "有效",
):
    return client.post(
        "/api/carrier/vehicles",
        headers=csrf,
        json={
            "plate_no": plate_no,
            "vehicle_type": "厢式货车",
            "length_m": 4.2,
            "max_load_kg": 5000,
            "owner_type": owner_type,
            "owner_driver_id": owner_driver_id,
            "document_status": document_status,
        },
    )


def _detail(client: TestClient, vehicle_id: int):
    return client.get(f"/api/carrier/vehicles/{vehicle_id}")


# 1. 公司车辆与司机个人车辆登记；列表展示全部字段；个人车辆默认关联所属司机
def test_register_company_and_personal_vehicles(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    driver = _create_driver(client, csrf, "driver-own", "李四")

    company = _create_vehicle(client, csrf, "京A00001")
    assert company.status_code == 201
    personal = _create_vehicle(
        client, csrf, "京A00002", owner_type="司机", owner_driver_id=driver["account_id"]
    )
    assert personal.status_code == 201

    listed = client.get("/api/carrier/vehicles")
    assert listed.status_code == 200
    rows = {row["plate_no"]: row for row in listed.json()}
    assert set(rows) == {"京A00001", "京A00002"}

    c = rows["京A00001"]
    assert c["vehicle_type"] == "厢式货车"
    assert c["length_m"] == 4.2
    assert c["max_load_kg"] == 5000
    assert c["owner_type"] == "公司"
    assert c["actual_owner"] == "顺达物流"
    assert c["current_driver"] == ""
    assert c["availability"] == "可用"
    assert c["lifecycle"] == "在册"
    assert c["document_status"] == "有效"

    p = rows["京A00002"]
    assert p["owner_type"] == "司机"
    assert p["actual_owner"] == "李四"
    assert p["current_driver"] == "李四"
    assert p["current_driver_id"] == driver["account_id"]

    # 司机视角投影出当前车辆车牌
    driver_view = client.get(f"/api/carrier/drivers/{driver['account_id']}")
    assert driver_view.json()["current_vehicle"] == "京A00002"


# 2. 公司将公司名下车辆分配给旗下司机，并投影到司机视图
def test_assign_company_vehicle_to_driver(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    driver = _create_driver(client, csrf, "driver-assign", "王五")
    vehicle = _create_vehicle(client, csrf, "京B00001")
    vehicle_id = vehicle.json()["id"]

    assigned = client.post(
        f"/api/carrier/vehicles/{vehicle_id}/assign",
        headers=csrf,
        json={"driver_account_id": driver["account_id"]},
    )
    assert assigned.status_code == 200
    assert assigned.json()["current_driver_id"] == driver["account_id"]
    assert assigned.json()["current_driver"] == "王五"
    # 分配不改动可用性 / 生命周期
    assert assigned.json()["availability"] == "可用"
    assert assigned.json()["lifecycle"] == "在册"

    driver_view = client.get(f"/api/carrier/drivers/{driver['account_id']}")
    assert driver_view.json()["current_vehicle"] == "京B00001"


# 3. 维修中 / 已停用 / 暂停使用的车辆不可分配，只有 可用+在册 才能分配
def test_unusable_vehicles_cannot_be_assigned(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    driver = _create_driver(client, csrf, "driver-target", "赵六")

    cases = [
        ("lifecycle", "维修中", "维修"),
        ("lifecycle", "已停用", "停用"),
        ("availability", "暂停使用", "暂停使用"),
    ]
    for index, (dimension, value, reason_fragment) in enumerate(cases):
        vehicle = _create_vehicle(client, csrf, f"京C0000{index + 1}")
        vehicle_id = vehicle.json()["id"]
        changed = client.post(
            f"/api/carrier/vehicles/{vehicle_id}/{dimension}",
            headers=csrf,
            json={dimension: value},
        )
        assert changed.status_code == 200
        assert changed.json()["assignable"] is False

        blocked = client.post(
            f"/api/carrier/vehicles/{vehicle_id}/assign",
            headers=csrf,
            json={"driver_account_id": driver["account_id"]},
        )
        assert 400 <= blocked.status_code < 500
        assert reason_fragment in blocked.json()["error"]["message"]
        assert _detail(client, vehicle_id).json()["current_driver_id"] is None

    good = _create_vehicle(client, csrf, "京C00009")
    assert good.json()["assignable"] is True
    ok = client.post(
        f"/api/carrier/vehicles/{good.json()['id']}/assign",
        headers=csrf,
        json={"driver_account_id": driver["account_id"]},
    )
    assert ok.status_code == 200


# 4. 可用性与生命周期是两个独立维度，改其一不动另一
def test_availability_and_lifecycle_are_independent(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    vehicle = _create_vehicle(client, csrf, "京D00001")
    vehicle_id = vehicle.json()["id"]

    paused = client.post(
        f"/api/carrier/vehicles/{vehicle_id}/availability",
        headers=csrf,
        json={"availability": "暂停使用"},
    )
    assert paused.status_code == 200
    assert paused.json()["availability"] == "暂停使用"
    assert paused.json()["lifecycle"] == "在册"

    repaired = client.post(
        f"/api/carrier/vehicles/{vehicle_id}/lifecycle",
        headers=csrf,
        json={"lifecycle": "维修中"},
    )
    assert repaired.status_code == 200
    assert repaired.json()["lifecycle"] == "维修中"
    assert repaired.json()["availability"] == "暂停使用"

    restored = client.post(
        f"/api/carrier/vehicles/{vehicle_id}/availability",
        headers=csrf,
        json={"availability": "可用"},
    )
    assert restored.status_code == 200
    assert restored.json()["availability"] == "可用"
    assert restored.json()["lifecycle"] == "维修中"
    assert restored.json()["assignable"] is False


# 5. 跨物流公司的车辆访问一律 404（列、详情、分配、改状态）
def test_cross_carrier_vehicle_access_is_404(client):
    _seed_carrier(client, "carrier-a")
    _seed_carrier(client, "carrier-b")
    csrf_a = _carrier_login(client, "carrier-a")
    vehicle_id = _create_vehicle(client, csrf_a, "京E00001").json()["id"]
    driver_a = _create_driver(client, csrf_a, "driver-a", "公司A司机")

    csrf_b = _carrier_login(client, "carrier-b")
    listed_b = client.get("/api/carrier/vehicles")
    assert listed_b.status_code == 200
    assert [row["plate_no"] for row in listed_b.json()] == []

    assert _detail(client, vehicle_id).status_code == 404
    assert (
        client.post(
            f"/api/carrier/vehicles/{vehicle_id}/assign",
            headers=csrf_b,
            json={"driver_account_id": driver_a["account_id"]},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/carrier/vehicles/{vehicle_id}/lifecycle",
            headers=csrf_b,
            json={"lifecycle": "已停用"},
        ).status_code
        == 404
    )


# 6. 不可物理删除：停用后仍在册于列表，且可被筛出；无 DELETE 端点
def test_no_physical_delete_and_filterable_assignable(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    good = _create_vehicle(client, csrf, "京F00001")
    bad = _create_vehicle(client, csrf, "京F00002")
    client.post(
        f"/api/carrier/vehicles/{bad.json()['id']}/lifecycle",
        headers=csrf,
        json={"lifecycle": "已停用"},
    )

    all_rows = client.get("/api/carrier/vehicles").json()
    assert {row["plate_no"] for row in all_rows} == {"京F00001", "京F00002"}
    stopped = _detail(client, bad.json()["id"]).json()
    assert stopped["lifecycle"] == "已停用"

    assignable = client.get("/api/carrier/vehicles", params={"assignable": True}).json()
    assert [row["plate_no"] for row in assignable] == ["京F00001"]

    assert client.delete(f"/api/carrier/vehicles/{good.json()['id']}").status_code == 405


# 7. 个人车辆必须关联本公司司机，否则拒绝（越权主体）
def test_personal_vehicle_requires_owned_driver(client):
    _seed_carrier(client, "carrier-a")
    _seed_carrier(client, "carrier-b")
    driver_b = _create_driver(client, _carrier_login(client, "carrier-b"), "driver-b", "外公司司机")
    csrf_a = _carrier_login(client, "carrier-a")

    rejected = _create_vehicle(
        client,
        csrf_a,
        "京G00001",
        owner_type="司机",
        owner_driver_id=driver_b["account_id"],
    )
    assert rejected.status_code == 404


# 8. 其他角色 / 未审核通过的物流公司不可访问车辆管理
def test_vehicle_management_requires_active_carrier(client):
    _seed_carrier(client)
    assert _login(client, "admin", "admin123456").status_code == 200
    assert client.get("/api/carrier/vehicles").status_code == 404

    _seed_carrier(client, "carrier-pending", auth_status="待审核")
    csrf_pending = _csrf(_login(client, "carrier-pending", CARRIER_PASSWORD))
    assert client.get("/api/carrier/vehicles").status_code == 403
    assert _create_vehicle(client, csrf_pending, "京H00001").status_code == 403


# 9. 写操作必须带 CSRF
def test_vehicle_writes_require_csrf(client):
    _seed_carrier(client)
    csrf = _carrier_login(client)
    assert _create_vehicle(client, csrf, "京I00001").status_code == 201
    no_csrf = client.post(
        "/api/carrier/vehicles",
        json={
            "plate_no": "京I00002",
            "vehicle_type": "厢式货车",
            "length_m": 4.2,
            "max_load_kg": 5000,
            "owner_type": "公司",
        },
    )
    assert no_csrf.status_code == 403
