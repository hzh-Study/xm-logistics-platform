"""平台异常管理与车辆转籍 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。

覆盖管理员追加异常处理记录（actor/原因/结果/时间、原记录不覆盖）、车辆转籍在
进行中任务时被阻断与无任务时放行、转籍前后归属与历史任务车辆不变、管理员对业务
记录只读，以及平台异常通知进入业务站内信而非公告 / 通知内容通道。
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
    company_name: str = "",
    name: str = "",
    auth_status: str = "审核通过",
) -> int:
    """布置夹具：直接插入账号与 profile，仅用于准备。"""
    conn = _db(client)
    try:
        existing = conn.execute("SELECT id FROM accounts WHERE phone = ?", (phone,)).fetchone()
        if existing:
            return existing[0]
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            """INSERT INTO accounts
               (phone, role, account_status, auth_status, password_hash, created_at)
               VALUES (?, ?, '正常使用', ?, ?, ?)""",
            (phone, role, auth_status, hash_password(PASSWORD), _now()),
        )
        account_id = cursor.lastrowid
        if role == "物流公司":
            conn.execute(
                "INSERT INTO carrier_profiles (account_id, company_name, license_no) "
                "VALUES (?, ?, '')",
                (account_id, company_name or f"{phone}物流"),
            )
        elif role == "货主":
            conn.execute("INSERT INTO shipper_profiles (account_id) VALUES (?)", (account_id,))
        elif role == "司机":
            conn.execute(
                "INSERT INTO driver_profiles (account_id, name, license_no, binding_complete) "
                "VALUES (?, ?, '', 1)",
                (account_id, name or f"{phone}司机"),
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


def _seed_order(client: TestClient, shipper_id: int, order_no: str, carrier_id: int) -> int:
    conn = _db(client)
    try:
        cursor = conn.execute(
            """INSERT INTO orders
               (order_no, shipper_id, cargo_name, status, created_at, carrier_id)
               VALUES (?, ?, '钢材', '运输中', ?, ?)""",
            (order_no, shipper_id, _now(), carrier_id),
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
    status: str,
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


def _client(app_client: TestClient) -> TestClient:
    """独立 TestClient（独立 cookie 会话），用于同时扮演多个角色。"""
    return TestClient(app_client.app)


def _create_exception(client: TestClient, headers: dict, **overrides):
    body = {
        "category": "投诉",
        "subject": "运输延误投诉",
        "detail": "货主反映货物迟到两天，要求核实",
    }
    body.update(overrides)
    return client.post("/api/admin/platform-exceptions", json=body, headers=headers)


def _append_handling(client: TestClient, headers: dict, exception_id: int, **overrides):
    body = {"result": "已处理", "reason": "已联系双方核实并达成补偿方案"}
    body.update(overrides)
    return client.post(
        f"/api/admin/platform-exceptions/{exception_id}/handling", json=body, headers=headers
    )


def _transfer(client: TestClient, headers: dict, **overrides):
    body = {"to_carrier_id": 999, "reason": "公司主体变更，车辆转籍"}
    body.update(overrides)
    return client.post("/api/admin/vehicle-transfers", json=body, headers=headers)


def _error(resp) -> dict:
    return resp.json()["error"]


# 1. 管理员追加平台异常处理记录：actor 角色、原因、结果、时间可见，原记录不被覆盖
def test_admin_appends_platform_exception_handling_records(client: TestClient):
    subject = _seed_account(client, "subject1", "货主")
    headers = _login_admin(client)
    admin_id = client.get("/api/auth/me").json()["id"]

    created = _create_exception(
        client,
        headers,
        category="投诉",
        subject="运输延误投诉",
        detail="货主反映货物迟到两天",
        subject_account_id=subject,
    )
    assert created.status_code == 201, created.text
    original = created.json()
    assert original["exception_no"]
    assert original["category"] == "投诉"
    assert original["actor"] == "管理员"
    exception_id = original["id"]

    listed = client.get("/api/admin/platform-exceptions")
    assert listed.status_code == 200
    assert any(e["id"] == exception_id for e in listed.json())

    handled = _append_handling(
        client,
        headers,
        exception_id,
        result="已调解",
        reason="双方同意补偿 500 元",
        detail="已出具调解书",
    )
    assert handled.status_code == 201, handled.text
    record = handled.json()
    assert record["actor"] == "管理员"
    assert record["actor_id"] == admin_id
    assert record["result"] == "已调解"
    assert record["reason"] == "双方同意补偿 500 元"
    assert record["handled_at"] and "T" in record["handled_at"]

    detail = client.get(f"/api/admin/platform-exceptions/{exception_id}")
    assert detail.status_code == 200
    view = detail.json()
    assert view["exception"]["detail"] == original["detail"]
    assert view["exception"]["subject"] == original["subject"]
    assert len(view["handling_records"]) == 1
    assert view["handling_records"][0]["result"] == "已调解"

    # 再次追加：两条处理记录都在，原异常记录仍不被覆盖
    second = _append_handling(
        client, headers, exception_id, result="已归档", reason="补偿已履行完毕"
    )
    assert second.status_code == 201, second.text
    view2 = client.get(f"/api/admin/platform-exceptions/{exception_id}").json()
    assert len(view2["handling_records"]) == 2
    assert view2["exception"]["detail"] == original["detail"]
    assert {r["result"] for r in view2["handling_records"]} == {"已调解", "已归档"}

    # 处理记录只读：不存在 PUT / DELETE 路径
    assert client.put(
        f"/api/admin/platform-exceptions/{exception_id}/handling", json={}, headers=headers
    ).status_code == 405
    assert client.delete(
        f"/api/admin/platform-exceptions/{exception_id}/handling", headers=headers
    ).status_code == 405


# 2. 车辆存在进行中运输任务时转籍被阻断，返回 409 与明确原因
def test_transfer_blocked_when_vehicle_has_in_progress_task(client: TestClient):
    shipper = _seed_account(client, "s1", "货主")
    carrier_a = _seed_account(client, "carrier-a", "物流公司")
    carrier_b = _seed_account(client, "carrier-b", "物流公司")
    driver = _seed_account(client, "d1", "司机")
    vehicle = _seed_vehicle(client, carrier_a, "沪A10001")
    order = _seed_order(client, shipper, "YS-260301-0001", carrier_a)
    _seed_task(client, order, carrier_a, driver, vehicle, "TASK-260301-0001", "运输中")

    headers = _login_admin(client)
    resp = _transfer(client, headers, vehicle_id=vehicle, to_carrier_id=carrier_b)
    assert resp.status_code == 409, resp.text
    err = _error(resp)
    assert "转籍" in (err["code"] + err["message"])
    assert "运输中" in (err["code"] + err["message"])

    # 归属未改变、无转籍历史
    vehicles = client.get(
        "/api/admin/vehicles", params={"plate_no": "沪A10001"}
    ).json()
    assert vehicles[0]["carrier_id"] == carrier_a
    history = client.get(
        "/api/admin/vehicle-transfers", params={"vehicle_id": vehicle}
    ).json()
    assert history == []


# 3. 无进行中任务时转籍放行：保留前后归属，历史任务车辆信息不变
def test_transfer_allowed_and_keeps_history_and_task_vehicle(client: TestClient):
    shipper = _seed_account(client, "s2", "货主")
    carrier_a = _seed_account(client, "carrier-a2", "物流公司")
    carrier_b = _seed_account(client, "carrier-b2", "物流公司")
    driver = _seed_account(client, "d2", "司机")
    vehicle = _seed_vehicle(client, carrier_a, "沪A10002")
    order = _seed_order(client, shipper, "YS-260302-0001", carrier_a)
    task = _seed_task(client, order, carrier_a, driver, vehicle, "TASK-260302-0001", "已完成")

    headers = _login_admin(client)
    before_task = client.get(f"/api/admin/tasks/{task}").json()
    assert before_task["vehicle_plate"] == "沪A10002"

    resp = _transfer(client, headers, vehicle_id=vehicle, to_carrier_id=carrier_b)
    assert resp.status_code == 201, resp.text
    transfer = resp.json()
    assert transfer["actor"] == "管理员"
    assert transfer["plate_no"] == "沪A10002"
    assert transfer["before_carrier_id"] == carrier_a
    assert transfer["after_carrier_id"] == carrier_b

    vehicles = client.get(
        "/api/admin/vehicles", params={"plate_no": "沪A10002"}
    ).json()
    assert vehicles[0]["carrier_id"] == carrier_b

    history = client.get(
        "/api/admin/vehicle-transfers", params={"vehicle_id": vehicle}
    ).json()
    assert len(history) == 1
    assert history[0]["before_carrier_id"] == carrier_a
    assert history[0]["after_carrier_id"] == carrier_b

    # 历史任务中的车辆信息未被改写
    after_task = client.get(f"/api/admin/tasks/{task}").json()
    assert after_task["vehicle_plate"] == "沪A10002"
    assert after_task["vehicle_id"] == vehicle


# 4. 管理员不能直接改写业务记录，也不能通过异常处理改写认证/证件审核状态
def test_admin_readonly_and_exception_does_not_rewrite_review_status(client: TestClient):
    driver = _seed_account(client, "d3", "司机", name="违规司机")
    carrier = _seed_account(client, "carrier-c", "物流公司")
    vehicle = _seed_vehicle(client, carrier, "沪A10003")
    headers = _login_admin(client)

    # 业务记录写操作一律拒绝
    for method, path in [
        ("post", "/api/admin/orders"),
        ("put", "/api/admin/orders/1"),
        ("delete", "/api/admin/tasks/1"),
        ("post", "/api/admin/checkins/1"),
        ("post", "/api/admin/expenses"),
    ]:
        if method == "delete":
            resp = client.delete(path, headers=headers)
        else:
            resp = getattr(client, method)(path, json={}, headers=headers)
        assert resp.status_code == 403, (path, resp.text)

    # 管理员冒充业务角色写 → 404
    assert client.post("/api/shipper/orders", json={"cargo_name": "x"}, headers=headers).status_code == 404
    assert client.post("/api/carrier/tasks", json={}, headers=headers).status_code == 404

    # 司机违规异常处理：仅追加处理记录，不直接改认证/驾驶资格状态
    created = _create_exception(
        client,
        headers,
        category="司机违规",
        subject="违规司机",
        detail="司机多次无故拒单",
        subject_account_id=driver,
    )
    assert created.status_code == 201, created.text
    handled = _append_handling(
        client, headers, created.json()["id"], result="已处罚", reason="暂停接单资格"
    )
    assert handled.status_code == 201, handled.text

    drivers = client.get("/api/admin/drivers").json()
    target = next(d for d in drivers if d["account_id"] == driver)
    assert target["auth_status"] == "审核通过"
    vehicles = client.get("/api/admin/vehicles", params={"plate_no": "沪A10003"}).json()
    assert vehicles[0]["document_review_status"] == "待审核"


# 5. 平台异常处理结果进入业务站内信，而不是公告 / 通知内容通道
def test_platform_exception_notice_goes_to_business_inbox(client: TestClient):
    carrier = _seed_account(client, "carrier-inbox", "物流公司")
    headers = _login_admin(client)
    created = _create_exception(
        client,
        headers,
        category="费用纠纷",
        subject="报销费用争议",
        detail="司机与公司就报销费用产生争议",
        subject_account_id=carrier,
    )
    assert created.status_code == 201, created.text
    handled = _append_handling(
        client,
        headers,
        created.json()["id"],
        result="已处理",
        reason="公司同意按标准补报",
    )
    assert handled.status_code == 201, handled.text

    carrier_client = _client(client)
    _login(carrier_client, "carrier-inbox")
    notices = carrier_client.get("/api/carrier/notifications")
    assert notices.status_code == 200
    matching = [n for n in notices.json() if "平台异常" in n["title"]]
    assert matching, notices.text
    assert "已处理" in matching[0]["body"]
    assert "公司同意按标准补报" in matching[0]["body"]

    # 公告 / 通知内容通道不含该处理结果
    ann_titles = [a["title"] for a in client.get("/api/admin/announcements").json()]
    notice_titles = [n["title"] for n in client.get("/api/admin/notices").json()]
    assert not any("平台异常" in t for t in ann_titles + notice_titles)


# 6. 非管理员访问平台异常 / 转籍端点一律 404（BOLA）
def test_wrong_role_cannot_use_platform_exception_endpoints(client: TestClient):
    _seed_account(client, "s3", "货主")
    headers = _csrf(_login(client, "s3"))
    assert client.get("/api/admin/platform-exceptions", headers=headers).status_code == 404
    assert _create_exception(client, headers).status_code == 404
    assert client.get("/api/admin/vehicle-transfers", headers=headers).status_code == 404
    assert _transfer(client, headers).status_code == 404


# 7. 入参校验：类别枚举与处理原因必填
def test_platform_exception_input_validation(client: TestClient):
    headers = _login_admin(client)
    bad_category = _create_exception(client, headers, category="未知类别")
    assert bad_category.status_code == 422

    created = _create_exception(client, headers)
    assert created.status_code == 201, created.text
    missing_reason = client.post(
        f"/api/admin/platform-exceptions/{created.json()['id']}/handling",
        json={"result": "已处理"},
        headers=headers,
    )
    assert missing_reason.status_code == 422
