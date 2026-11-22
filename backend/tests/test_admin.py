"""管理员全平台查询与账号处置 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。

覆盖运营统计、全平台查询、统一认证审核（驳回原因必填）、账号禁用 / 恢复、
平台公告独立通道，以及管理员对业务记录只读。
"""

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password

ADMIN = ("admin", "admin123456")
PASSWORD = "pw123456"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db(client: TestClient) -> sqlite3.Connection:
    return sqlite3.connect(client.app.state.settings.db_path)


def _seed_account(
    client: TestClient,
    phone: str,
    role: str,
    *,
    auth_status: str = "审核通过",
    account_status: str = "正常使用",
    company_name: str = "",
    name: str = "",
    license_no: str = "",
) -> int:
    """布置夹具：直接插入一个账号与对应 profile，仅用于准备。"""
    conn = _db(client)
    try:
        existing = conn.execute("SELECT id FROM accounts WHERE phone = ?", (phone,)).fetchone()
        if existing:
            return existing[0]
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            """INSERT INTO accounts
               (phone, role, account_status, auth_status, password_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (phone, role, account_status, auth_status, hash_password(PASSWORD), _now()),
        )
        account_id = cursor.lastrowid
        if role == "货主":
            conn.execute(
                "INSERT INTO shipper_profiles (account_id, profile_type, company_name) "
                "VALUES (?, '企业', ?)",
                (account_id, company_name or f"{phone}货主"),
            )
        elif role == "物流公司":
            conn.execute(
                "INSERT INTO carrier_profiles (account_id, company_name, license_no) "
                "VALUES (?, ?, ?)",
                (account_id, company_name or f"{phone}物流", license_no),
            )
        elif role == "司机":
            conn.execute(
                """INSERT INTO driver_profiles
                   (account_id, name, license_no, binding_complete)
                   VALUES (?, ?, ?, 1)""",
                (account_id, name or f"{phone}司机", license_no),
            )
        conn.commit()
        return account_id
    finally:
        conn.close()


def _seed_vehicle(client: TestClient, carrier_id: int, plate_no: str) -> int:
    conn = _db(client)
    try:
        cursor = conn.execute(
            """INSERT INTO vehicles
               (plate_no, carrier_id, vehicle_type, length_m, max_load_kg,
                owner_type, availability, lifecycle, document_status, created_at, updated_at)
               VALUES (?, ?, '厢式货车', 8.0, 10000, '公司', '可用', '在册', '待审核', ?, ?)""",
            (plate_no, carrier_id, _now(), _now()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _seed_order(
    client: TestClient,
    shipper_id: int,
    order_no: str,
    status: str,
    created_at: str,
    carrier_id: int | None = None,
) -> int:
    conn = _db(client)
    try:
        cursor = conn.execute(
            """INSERT INTO orders
               (order_no, shipper_id, cargo_name, status, created_at, carrier_id)
               VALUES (?, ?, '钢材', ?, ?, ?)""",
            (order_no, shipper_id, status, created_at, carrier_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _seed_task(
    client: TestClient,
    order_id: int,
    carrier_id: int,
    driver_id: int,
    vehicle_id: int,
    task_no: str,
    status: str = "运输中",
) -> int:
    conn = _db(client)
    try:
        cursor = conn.execute(
            """INSERT INTO transport_tasks
               (task_no, order_id, carrier_id, driver_account_id, vehicle_id,
                status, planned_load_at, planned_deliver_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_no,
                order_id,
                carrier_id,
                driver_id,
                vehicle_id,
                status,
                "2026-03-01T09:00:00+08:00",
                "2026-03-02T09:00:00+08:00",
                _now(),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _login(client: TestClient, phone: str, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"phone": phone, "password": password})


def _csrf(resp) -> dict:
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _login_admin(client: TestClient) -> dict:
    return _csrf(_login(client, *ADMIN))


def _client(client: TestClient) -> TestClient:
    """独立的 TestClient（独立 cookie 会话），用于同时扮演多个角色。"""
    return TestClient(client.app)


def _codes(resp) -> set:
    """提取响应中的 error.code 集合，便于断言 422 字段错误。"""
    body = resp.json()
    if isinstance(body, dict) and "error" in body:
        details = body["error"].get("details") or []
        return {item.get("field") for item in details if isinstance(item, dict)}
    return set()


def test_admin_stats_after_seeded_data(client: TestClient):
    """管理员首页统计反映货主/公司/司机/车辆、订单状态与待审核认证数量。"""
    _seed_account(client, "s1", "货主", auth_status="待审核")
    _seed_account(client, "s2", "货主")
    carrier_id = _seed_account(client, "c1", "物流公司")
    _seed_account(client, "d1", "司机")
    _seed_account(client, "d2", "司机")
    _seed_account(client, "d3", "司机")
    _seed_vehicle(client, carrier_id, "沪A00001")
    _seed_vehicle(client, carrier_id, "沪A00002")

    _seed_order(client, 1, "YS-260101-0001", "待承接", "2026-01-01T09:00:00+08:00")
    _seed_order(client, 1, "YS-260101-0002", "待承接", "2026-01-02T09:00:00+08:00")
    _seed_order(client, 2, "YS-260101-0003", "运输中", "2026-01-03T09:00:00+08:00")
    _seed_order(client, 2, "YS-260101-0004", "已完成", "2026-01-04T09:00:00+08:00")
    _seed_order(client, 2, "YS-260101-0005", "异常处理中", "2026-01-05T09:00:00+08:00")

    headers = _login_admin(client)
    resp = client.get("/api/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["shipper_count"] == 2
    assert data["carrier_count"] == 1
    assert data["driver_count"] == 3
    assert data["vehicle_count"] == 2
    assert data["orders_pending_accept"] == 2
    assert data["orders_in_transit"] == 1
    assert data["orders_completed"] == 1
    assert data["orders_exception"] == 1
    assert data["pending_certifications"] == 1


def test_platform_order_query_filters(client: TestClient):
    """可按编号/货主/公司/状态/发布时间查询全平台运输订单。"""
    s1 = _seed_account(client, "s1", "货主", company_name="甲供应链")
    carrier_id = _seed_account(client, "c1", "物流公司", company_name="乙物流")
    _seed_order(client, s1, "YS-260101-0001", "待承接", "2026-01-05T09:00:00+08:00")
    _seed_order(
        client, s1, "YS-260101-0002", "运输中", "2026-02-10T09:00:00+08:00", carrier_id
    )
    _seed_order(
        client, s1, "YS-260101-0003", "已完成", "2026-03-15T09:00:00+08:00", carrier_id
    )

    headers = _login_admin(client)

    def query(params: dict) -> list[dict]:
        resp = client.get("/api/admin/orders", params=params)
        assert resp.status_code == 200, resp.text
        return resp.json()

    assert [o["order_no"] for o in query({"order_no": "0002"})] == ["YS-260101-0002"]
    assert len(query({"shipper": "甲供应链"})) == 3
    assert {o["order_no"] for o in query({"company": "乙物流"})} == {
        "YS-260101-0002",
        "YS-260101-0003",
    }
    assert [o["order_no"] for o in query({"status": "已完成"})] == ["YS-260101-0003"]
    assert [o["order_no"] for o in query({
        "published_from": "2026-02-01T00:00:00+08:00",
        "published_to": "2026-02-28T23:59:59+08:00",
    })] == ["YS-260101-0002"]

    detail = client.get("/api/admin/orders/2")
    assert detail.status_code == 200
    assert detail.json()["order_no"] == "YS-260101-0002"


def test_platform_task_query_and_detail(client: TestClient):
    """可查询全平台运输任务并查看详情，支持状态与订单筛选。"""
    s1 = _seed_account(client, "s1", "货主")
    carrier_id = _seed_account(client, "c1", "物流公司")
    driver_id = _seed_account(client, "d1", "司机")
    vehicle_id = _seed_vehicle(client, carrier_id, "沪B00001")
    order_id = _seed_order(
        client, s1, "YS-260101-0001", "运输中", "2026-02-01T09:00:00+08:00", carrier_id
    )
    task_id = _seed_task(
        client, order_id, carrier_id, driver_id, vehicle_id, "TASK-260201-0001", "运输中"
    )
    _seed_task(
        client, order_id, carrier_id, driver_id, vehicle_id, "TASK-260201-0002", "已完成"
    )

    _login_admin(client)
    running = client.get("/api/admin/tasks", params={"status": "运输中"})
    assert running.status_code == 200
    assert [t["task_no"] for t in running.json()] == ["TASK-260201-0001"]

    by_order = client.get("/api/admin/tasks", params={"order_id": order_id})
    assert len(by_order.json()) == 2

    detail = client.get(f"/api/admin/tasks/{task_id}")
    assert detail.status_code == 200
    assert detail.json()["task_no"] == "TASK-260201-0001"
    assert detail.json()["vehicle_plate"] == "沪B00001"


def test_platform_entity_queries(client: TestClient):
    """可查询全平台货主、司机与车辆。"""
    _seed_account(client, "s1", "货主", company_name="甲供应链")
    carrier_id = _seed_account(client, "c1", "物流公司", company_name="乙物流")
    _seed_account(client, "d1", "司机", name="王司机", license_no="L1")
    _seed_vehicle(client, carrier_id, "沪C00001")

    _login_admin(client)
    shippers = client.get("/api/admin/shippers")
    assert shippers.status_code == 200
    assert [s["company_name"] for s in shippers.json()] == ["甲供应链"]

    carriers = client.get("/api/admin/carriers")
    assert carriers.status_code == 200
    assert [c["company_name"] for c in carriers.json()] == ["乙物流"]

    drivers = client.get("/api/admin/drivers")
    assert drivers.status_code == 200
    assert drivers.json()[0]["driver_name"] == "王司机"

    vehicles = client.get("/api/admin/vehicles", params={"plate_no": "沪C00001"})
    assert vehicles.status_code == 200
    assert [v["plate_no"] for v in vehicles.json()] == ["沪C00001"]


def test_unified_certifications_list(client: TestClient):
    """统一列表覆盖货主/企业/司机/驾驶资格/车辆证件五类认证。"""
    s1 = _seed_account(client, "s1", "货主", auth_status="待审核")
    c1 = _seed_account(client, "c1", "物流公司", auth_status="待审核", license_no="E1")
    d1 = _seed_account(client, "d1", "司机", auth_status="待审核", license_no="L1")
    _seed_vehicle(client, c1, "沪D00001")

    conn = _db(client)
    try:
        conn.execute(
            """INSERT INTO shipper_certifications
               (account_id, cert_type, name, id_number, contact_phone, documents, created_at)
               VALUES (?, '企业', '甲供应链', 'ID1', '13800000001', '[]', ?)""",
            (s1, _now()),
        )
        conn.execute(
            """INSERT INTO carrier_certifications
               (account_id, kind, company_name, license_no, actor, created_at)
               VALUES (?, '提交', '乙物流', 'E1', '物流公司', ?)""",
            (c1, _now()),
        )
        conn.commit()
    finally:
        conn.close()

    _login_admin(client)
    resp = client.get("/api/admin/certifications")
    assert resp.status_code == 200, resp.text
    categories = {item["category"] for item in resp.json()}
    assert categories == {"货主", "企业", "司机", "驾驶资格", "车辆证件"}

    only_vehicle = client.get(
        "/api/admin/certifications", params={"category": "车辆证件"}
    )
    assert only_vehicle.status_code == 200
    assert {item["category"] for item in only_vehicle.json()} == {"车辆证件"}


def test_unified_review_requires_reason_and_updates_status(client: TestClient):
    """统一审核驳回原因必填；审核后状态与原因在列表可见，原记录不被改写。"""
    s1 = _seed_account(client, "s1", "货主", auth_status="待审核")
    c1 = _seed_account(client, "c1", "物流公司", auth_status="待审核", license_no="E1")
    d1 = _seed_account(client, "d1", "司机", auth_status="待审核", license_no="L1")
    vehicle_id = _seed_vehicle(client, c1, "沪E00001")

    conn = _db(client)
    try:
        conn.execute(
            """INSERT INTO shipper_certifications
               (account_id, cert_type, name, id_number, contact_phone, documents, created_at)
               VALUES (?, '企业', '甲供应链', 'ID1', '13800000001', '[]', ?)""",
            (s1, _now()),
        )
        conn.execute(
            """INSERT INTO carrier_certifications
               (account_id, kind, company_name, license_no, actor, created_at)
               VALUES (?, '提交', '乙物流', 'E1', '物流公司', ?)""",
            (c1, _now()),
        )
        conn.commit()
    finally:
        conn.close()

    headers = _login_admin(client)

    missing = client.post(
        "/api/admin/certifications/review",
        json={"category": "司机", "target_id": d1, "decision": "审核不通过"},
        headers=headers,
    )
    assert missing.status_code == 422
    assert "驳回原因必填" in missing.text

    # 通过：车辆证件审核状态变为有效
    approved = client.post(
        "/api/admin/certifications/review",
        json={
            "category": "车辆证件",
            "target_id": vehicle_id,
            "decision": "审核通过",
            "reason": "",
        },
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    vehicle_items = client.get(
        "/api/admin/certifications", params={"category": "车辆证件"}
    ).json()
    assert vehicle_items[0]["auth_status"] == "有效"

    # 驳回：企业认证状态变为审核不通过，原因在列表可见
    rejected = client.post(
        "/api/admin/certifications/review",
        json={
            "category": "企业",
            "target_id": c1,
            "decision": "审核不通过",
            "reason": "资质不全",
        },
        headers=headers,
    )
    assert rejected.status_code == 200, rejected.text
    carrier_items = client.get(
        "/api/admin/certifications", params={"category": "企业"}
    ).json()
    assert carrier_items[0]["auth_status"] == "审核不通过"
    assert "资质不全" in (carrier_items[0].get("reason") or "")


def test_disable_and_restore_account(client: TestClient):
    """管理员禁用账号后该账号不可用、会话被撤销；恢复后可重新登录。"""
    carrier_id = _seed_account(client, "c1", "物流公司")
    admin_headers = _login_admin(client)

    carrier_client = _client(client)
    _login(carrier_client, "c1")
    assert carrier_client.get("/api/carrier/workbench").status_code == 200

    disabled = client.post(
        f"/api/admin/accounts/{carrier_id}/status",
        json={"account_status": "已禁用"},
        headers=admin_headers,
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["account_status"] == "已禁用"
    assert carrier_client.get("/api/carrier/workbench").status_code in (401, 403)

    restored = client.post(
        f"/api/admin/accounts/{carrier_id}/status",
        json={"account_status": "正常使用"},
        headers=admin_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["account_status"] == "正常使用"
    assert _login(carrier_client, "c1").status_code == 200
    assert carrier_client.get("/api/carrier/workbench").status_code == 200

    carriers = client.get("/api/admin/carriers").json()
    assert carriers[0]["account_status"] == "正常使用"


def test_announcements_and_notices_not_in_business_channel(client: TestClient):
    """公告/通知通过独立内容通道发布，不出现在业务站内通知里。"""
    headers = _login_admin(client)
    created = client.post(
        "/api/admin/announcements",
        json={"title": "系统升级通知", "body": "本周日 22:00 升级维护"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["channel"] == "平台公告"

    listed = client.get("/api/admin/announcements")
    assert listed.status_code == 200
    assert any(a["title"] == "系统升级通知" for a in listed.json())

    notice = client.post(
        "/api/admin/notices",
        json={"title": "实名认证提醒", "body": "请尽快完成认证"},
        headers=headers,
    )
    assert notice.status_code == 201
    assert notice.json()["channel"] == "平台通知"
    assert any(n["title"] == "实名认证提醒" for n in client.get("/api/admin/notices").json())

    s1 = _seed_account(client, "s1", "货主")
    c1 = _seed_account(client, "c1", "物流公司")
    shipper_client = _client(client)
    carrier_client = _client(client)
    _login(shipper_client, "s1")
    _login(carrier_client, "c1")
    titles = {
        item["title"]
        for item in (
            shipper_client.get("/api/shipper/notifications").json()
            + carrier_client.get("/api/carrier/notifications").json()
        )
    }
    assert "系统升级通知" not in titles
    assert "实名认证提醒" not in titles


def test_admin_business_writes_rejected(client: TestClient):
    """管理员对订单/任务/费用等业务记录只读，写操作被拒绝。"""
    headers = _login_admin(client)

    write_paths = [
        ("post", "/api/admin/orders"),
        ("put", "/api/admin/orders/1"),
        ("delete", "/api/admin/orders/1"),
        ("post", "/api/admin/tasks"),
        ("delete", "/api/admin/tasks/1"),
        ("post", "/api/admin/checkins/1"),
        ("post", "/api/admin/expenses"),
    ]
    for method, path in write_paths:
        if method == "delete":
            resp = client.delete(path, headers=headers)
        else:
            resp = getattr(client, method)(path, json={}, headers=headers)
        assert resp.status_code == 403, (path, resp.status_code, resp.text)

    # 管理员也不能冒充业务角色写业务记录（角色门禁返回 404）
    publish = client.post("/api/shipper/orders", json={"cargo_name": "x"}, headers=headers)
    assert publish.status_code == 404
    dispatch = client.post("/api/carrier/tasks", json={}, headers=headers)
    assert dispatch.status_code == 404


def test_wrong_role_cannot_use_admin_endpoints(client: TestClient):
    """非管理员访问管理端点返回 404（BOLA）。"""
    _seed_account(client, "s1", "货主")
    headers = _csrf(_login(client, "s1"))
    assert client.get("/api/admin/stats").status_code == 404
    assert client.get("/api/admin/orders").status_code == 404
    assert client.get("/api/admin/certifications").status_code == 404
    rejected = client.post(
        "/api/admin/announcements",
        json={"title": "x", "body": "y"},
        headers=headers,
    )
    assert rejected.status_code == 404
