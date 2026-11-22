"""订单取消与终止运输 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。

覆盖未承接直接取消、已承接未起运原因必填与公司同意/驳回、在途无取消入口仅
终止运输置已取消、已完成与待确认完成不可取消、两种处理中状态互斥、通知、
追加留痕不覆盖原记录与跨主体 404。
"""

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password

PASSWORD = "pw123456"
TEMP_PASSWORD = "temp123456"
NEW_PASSWORD = "new123456"


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
) -> int:
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
        if role == "物流公司":
            conn.execute(
                "INSERT INTO carrier_profiles (account_id, company_name, license_no) "
                "VALUES (?, ?, '')",
                (account_id, f"{phone}物流"),
            )
        elif role == "货主":
            conn.execute("INSERT INTO shipper_profiles (account_id) VALUES (?)", (account_id,))
        conn.commit()
        return account_id
    finally:
        conn.close()


def _login(client: TestClient, phone: str, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"phone": phone, "password": password})


def _csrf(resp) -> dict:
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _login_headers(client: TestClient, phone: str, password: str = PASSWORD) -> dict:
    return _csrf(_login(client, phone, password))


def _client(app_client: TestClient) -> TestClient:
    return TestClient(app_client.app)


def _publish(client: TestClient, headers: dict, **overrides):
    body = {
        "cargo_name": "冷轧钢板",
        "cargo_type": "钢材",
        "weight": "50000 kg",
        "quantity": "50 吨",
        "load_requirement": "30 吨以上",
        "shipping_source": "临时地址",
        "shipping_name": "上海发货点",
        "shipping_contact": "王发货",
        "shipping_phone": "13800000001",
        "shipping_province": "上海市",
        "shipping_city": "上海市",
        "shipping_district": "浦东新区",
        "shipping_detail_address": "张江路 100 号",
        "receiving_name": "苏州收货方",
        "receiving_contact": "李收货",
        "receiving_phone": "13900000002",
        "receiving_province": "江苏省",
        "receiving_city": "苏州市",
        "receiving_district": "工业园区",
        "receiving_detail_address": "星湖街 200 号",
        "quote_method": "固定",
        "quote_amount_yuan": "1200.50",
    }
    body.update(overrides)
    return client.post("/api/shipper/orders", json=body, headers=headers)


def _create_driver(client: TestClient, headers: dict, phone: str, name: str = "张三") -> dict:
    resp = client.post(
        "/api/carrier/drivers",
        headers=headers,
        json={"phone": phone, "password": TEMP_PASSWORD, "name": name},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _onboard_driver(app_client: TestClient, phone: str) -> TestClient:
    drv = _client(app_client)
    login = _login(drv, phone, TEMP_PASSWORD)
    assert login.status_code == 200, login.text
    headers = _csrf(login)
    changed = drv.post(
        "/api/driver/change-password",
        headers=headers,
        json={"new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 204, changed.text
    binding = drv.post(
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
    assert binding.status_code == 200, binding.text
    return drv


def _create_vehicle(client: TestClient, headers: dict, plate: str) -> dict:
    resp = client.post(
        "/api/carrier/vehicles",
        headers=headers,
        json={
            "plate_no": plate,
            "vehicle_type": "平板货车",
            "length_m": 13.0,
            "max_load_kg": 30000,
            "owner_type": "公司",
            "document_status": "有效",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _driver_headers(drv: TestClient, phone: str) -> dict:
    return _csrf(_login(drv, phone, NEW_PASSWORD))


class Fixture:
    """完整链路夹具：货主 + 物流公司 + 已发布订单。"""

    def __init__(self, client: TestClient, carrier_phone: str = "carrier1"):
        self.app = client
        self.carrier_id = _seed_account(client, carrier_phone, "物流公司")
        self.shipper_id = _seed_account(client, "shipper1", "货主")
        self.shipper = client
        self.shipper_headers = _login_headers(client, "shipper1")
        self.carrier = _client(client)
        self.carrier_headers = _login_headers(self.carrier, carrier_phone)
        published = _publish(self.shipper, self.shipper_headers)
        assert published.status_code == 201, published.text
        self.order = published.json()
        self.task = None
        self.drv = None
        self.driver_headers = None

    def accept(self) -> dict:
        resp = self.carrier.post(
            f"/api/carrier/order-pool/{self.order['id']}/accept",
            headers=self.carrier_headers,
        )
        assert resp.status_code == 200, resp.text
        self.order = resp.json()
        return self.order

    def dispatch(self, phone: str = "cancel-driver1", plate: str = "京A02001") -> dict:
        info = _create_driver(self.carrier, self.carrier_headers, phone)
        self.drv = _onboard_driver(self.app, phone)
        self.driver_headers = _driver_headers(self.drv, phone)
        vehicle = _create_vehicle(self.carrier, self.carrier_headers, plate)
        resp = self.carrier.post(
            "/api/carrier/tasks",
            headers=self.carrier_headers,
            json={
                "order_id": self.order["id"],
                "driver_account_id": info["account_id"],
                "vehicle_id": vehicle["id"],
                "planned_load_at": "2026-11-23T10:00:00+00:00",
                "planned_deliver_at": "2026-11-24T10:00:00+00:00",
                "notes": "注意防潮",
            },
        )
        assert resp.status_code == 201, resp.text
        accepted = self.drv.post(f"/api/driver/tasks/{resp.json()['id']}/accept", headers=self.driver_headers)
        assert accepted.status_code == 200, accepted.text
        self.task = resp.json()
        return self.task

    def start_transport(self) -> None:
        task_id = self.task["id"]
        checkin = self.drv.post(
            f"/api/driver/tasks/{task_id}/checkin",
            headers=self.driver_headers,
            json={
                "latitude": 31.2,
                "longitude": 121.5,
                "arrived_at": "2026-11-23T09:55:00+00:00",
                "photos": ["vouchers/checkin/site.jpg"],
                "notes": "已到发货点",
            },
        )
        assert checkin.status_code == 201, checkin.text
        for phase in ("装货前", "装货中", "装货完成"):
            resp = self.drv.post(
                f"/api/driver/tasks/{task_id}/loading/photos",
                headers=self.driver_headers,
                json={"phase": phase, "paths": [f"vouchers/loading/{phase}.jpg"]},
            )
            assert resp.status_code == 201, resp.text
        started = self.drv.post(
            f"/api/driver/tasks/{task_id}/start-transport",
            headers=self.driver_headers,
            json={"cargo_confirmed": True, "vehicle_confirmed": True, "notes": "核对无误"},
        )
        assert started.status_code == 200, started.text

    def force_order_status(self, status: str) -> None:
        conn = _db(self.app)
        try:
            conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, self.order["id"]))
            conn.commit()
        finally:
            conn.close()

    def force_task_status(self, status: str) -> None:
        conn = _db(self.app)
        try:
            conn.execute("UPDATE transport_tasks SET status = ? WHERE id = ?", (status, self.task["id"]))
            conn.commit()
        finally:
            conn.close()


def _apply(client: TestClient, headers: dict, order_id: int, **body):
    return client.post(
        f"/api/shipper/orders/{order_id}/cancel",
        headers=headers,
        json=body,
    )


def _options(client: TestClient, headers: dict, order_id: int):
    return client.get(f"/api/shipper/orders/{order_id}/cancel-options", headers=headers)


def _view(client: TestClient, headers: dict, order_id: int):
    return client.get(f"/api/shipper/orders/{order_id}/cancel", headers=headers)


def _carrier_list(client: TestClient, headers: dict):
    return client.get("/api/carrier/cancel-applications", headers=headers)


def _agree(client: TestClient, headers: dict, application_id: int):
    return client.post(f"/api/carrier/cancel-applications/{application_id}/agree", headers=headers)


def _reject(client: TestClient, headers: dict, application_id: int, reason: str):
    return client.post(
        f"/api/carrier/cancel-applications/{application_id}/reject",
        headers=headers,
        json={"reason": reason},
    )


def _order_status(f: Fixture) -> str:
    resp = f.shipper.get(f"/api/shipper/orders/{f.order['id']}")
    assert resp.status_code == 200, resp.text
    return resp.json()["status"]


def _notifications(client: TestClient, headers: dict) -> list[dict]:
    resp = client.get("/api/shipper/notifications", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _carrier_notifications(f: Fixture) -> list[dict]:
    resp = f.carrier.get("/api/carrier/notifications", headers=f.carrier_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# 1. 未承接订单：货主直接取消，订单置已取消并落通知与留痕
def test_unaccepted_order_direct_cancel(client):
    f = Fixture(client)

    resp = _apply(f.shipper, f.shipper_headers, f.order["id"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["mode"] == "直接取消"
    assert body["status"] == "已直接取消"
    assert body["before_status"] == "待承接"
    assert body["after_status"] == "已取消"

    assert _order_status(f) == "已取消"
    view = _view(f.shipper, f.shipper_headers, f.order["id"]).json()
    assert [item["event"] for item in view["audit"]] == ["申请", "直接取消"]
    assert any(n["kind"] == "取消结果" and "已取消" in n["body"] for n in _notifications(f.shipper, f.shipper_headers))


# 2. 已承接但未起运：原因必填；提交后订单进入取消处理中，公司收到通知
def test_accepted_not_started_requires_reason_and_enters_cancel_processing(client):
    f = Fixture(client)
    f.accept()

    options = _options(f.shipper, f.shipper_headers, f.order["id"])
    assert options.status_code == 200, options.text
    assert options.json()["can_cancel"] is True
    assert options.json()["mode"] == "公司确认"

    missing = _apply(f.shipper, f.shipper_headers, f.order["id"])
    assert missing.status_code == 409, missing.text
    assert "原因必填" in missing.json()["error"]["code"]
    empty = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="   ")
    assert empty.status_code == 409, empty.text

    resp = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="货物不再需要")
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "待公司处理"
    assert resp.json()["reason"] == "货物不再需要"
    assert _order_status(f) == "取消处理中"
    assert any(n["kind"] == "取消申请" for n in _carrier_notifications(f))


# 3. 公司同意：订单置已取消，货主收到通知，追加同意留痕
def test_carrier_agree_sets_order_cancelled(client):
    f = Fixture(client)
    f.accept()
    application = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="客户撤单").json()

    resp = _agree(f.carrier, f.carrier_headers, application["id"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "已同意"
    assert resp.json()["after_status"] == "已取消"

    assert _order_status(f) == "已取消"
    view = _view(f.shipper, f.shipper_headers, f.order["id"]).json()
    assert [item["event"] for item in view["audit"]] == ["申请", "同意"]
    assert any(n["kind"] == "取消结果" and "已同意" in n["body"] for n in _notifications(f.shipper, f.shipper_headers))


# 4. 公司驳回：订单恢复到申请前状态并写明原因，货主收到含原因通知
def test_carrier_reject_restores_status_with_reason(client):
    f = Fixture(client)
    f.accept()
    application = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="想改期").json()

    resp = _reject(f.carrier, f.carrier_headers, application["id"], "仓内货已备好，请勿取消")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "已驳回"
    assert resp.json()["after_status"] == "已承接"

    assert _order_status(f) == "已承接"
    view = _view(f.shipper, f.shipper_headers, f.order["id"]).json()
    assert [item["event"] for item in view["audit"]] == ["申请", "驳回"]
    assert view["audit"][-1]["reason"] == "仓内货已备好，请勿取消"
    assert any("仓内货已备好" in n["body"] for n in _notifications(f.shipper, f.shipper_headers))

    missing = _reject(f.carrier, f.carrier_headers, application["id"], "")
    assert missing.status_code == 422, missing.text


# 5. 已起运：不提供取消入口，进入异常处理中；取消申请被拒并引导异常处理
def test_in_transit_has_no_cancel_entry_and_enters_exception_processing(client):
    f = Fixture(client)
    f.accept()
    f.dispatch()
    f.start_transport()

    options = _options(f.shipper, f.shipper_headers, f.order["id"])
    assert options.status_code == 200, options.text
    assert options.json()["can_cancel"] is False
    assert "异常" in options.json()["message"]

    apply = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="中途取消")
    assert apply.status_code == 409, apply.text
    assert "异常" in apply.json()["error"]["code"]

    task_id = f.task["id"]
    anomaly = f.drv.post(
        f"/api/driver/tasks/{task_id}/anomalies",
        headers=f.driver_headers,
        json={
            "kind": "故障",
            "detail": "发动机异响",
            "photos": ["vouchers/exc/scene.jpg"],
            "occurred_at": "2026-11-24T09:30:00+00:00",
        },
    )
    assert anomaly.status_code == 201, anomaly.text
    assert _order_status(f) == "异常处理中"


# 6. 在途仅「终止运输」可置已取消并写明原因（复用 #12 异常处理结果）
def test_terminate_transport_via_exception_cancels_order(client):
    f = Fixture(client)
    f.accept()
    f.dispatch()
    f.start_transport()
    task_id = f.task["id"]
    anomaly = f.drv.post(
        f"/api/driver/tasks/{task_id}/anomalies",
        headers=f.driver_headers,
        json={
            "kind": "事故",
            "detail": "车辆报废",
            "photos": ["vouchers/exc/scene.jpg"],
            "occurred_at": "2026-11-24T09:30:00+00:00",
        },
    ).json()
    handled = f.carrier.post(
        f"/api/carrier/tasks/{task_id}/exceptions/{anomaly['id']}/handle",
        headers=f.carrier_headers,
        json={"result": "终止运输", "detail": "车辆报废，无法继续运输"},
    )
    assert handled.status_code == 201, handled.text
    assert handled.json()["order_status"] == "已取消"
    assert _order_status(f) == "已取消"
    view = f.carrier.get(f"/api/carrier/tasks/{task_id}/exceptions").json()
    assert view["handling_records"][0]["result"] == "终止运输"
    assert view["handling_records"][0]["reason"] == "车辆报废，无法继续运输"


# 7. 已完成运输不能取消
def test_completed_order_cannot_cancel(client):
    f = Fixture(client)
    f.force_order_status("已完成")

    options = _options(f.shipper, f.shipper_headers, f.order["id"])
    assert options.status_code == 200, options.text
    assert options.json()["can_cancel"] is False
    apply = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="想取消")
    assert apply.status_code == 409, apply.text
    assert "已完成" in apply.json()["error"]["code"]


# 8. 待确认完成（签收凭证待公司确认）不能取消
def test_awaiting_voucher_confirmation_cannot_cancel(client):
    f = Fixture(client)
    f.accept()
    f.dispatch()
    f.force_task_status("待确认完成")

    apply = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="想取消")
    assert apply.status_code == 409, apply.text
    assert "凭证" in apply.json()["error"]["code"]


# 9. 取消处理中与异常处理中互斥，且取消处理中不可重复申请
def test_cancel_processing_and_exception_processing_are_mutually_exclusive(client):
    f = Fixture(client)
    f.accept()
    application = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="重复申请").json()
    assert _order_status(f) == "取消处理中"

    again = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="再来一次")
    assert again.status_code == 409, again.text
    assert "取消处理中" in again.json()["error"]["code"]

    # 订单处于取消处理中时，不能被置为异常处理中（互斥硬约束）
    conn = _db(client)
    try:
        import pytest

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE orders SET status = '异常处理中' WHERE id = ?", (f.order["id"],)
            )
        conn.rollback()
    finally:
        conn.close()
    assert _order_status(f) == "取消处理中"

    # 反向：异常处理中的订单不能再申请取消
    other = Fixture(client, "carrier2")
    other.force_order_status("异常处理中")
    blocked = _apply(other.shipper, other.shipper_headers, other.order["id"], reason="异常中取消")
    assert blocked.status_code == 409, blocked.text
    assert "异常" in blocked.json()["error"]["code"]
    assert application["status"] == "待公司处理"


# 10. 同意/驳回后再次申请：留痕追加，不覆盖原记录
def test_audit_is_append_only_across_actions(client):
    f = Fixture(client)
    f.accept()
    first = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="第一次").json()
    _reject(f.carrier, f.carrier_headers, first["id"], "公司不同意")
    second = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="第二次").json()
    _agree(f.carrier, f.carrier_headers, second["id"])

    view = _view(f.shipper, f.shipper_headers, f.order["id"]).json()
    assert [item["event"] for item in view["audit"]] == ["申请", "驳回", "申请", "同意"]
    assert [item["reason"] for item in view["audit"]] == ["第一次", "公司不同意", "第二次", ""]
    assert len(view["audit"]) == 4
    assert second["id"] != first["id"]
    assert _order_status(f) == "已取消"


# 11. 取消记录无更新/删除端点（只读）；列表与详情可读
def test_cancel_records_are_read_only_and_listable(client):
    f = Fixture(client)
    f.accept()
    application = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="只读校验").json()

    detail = f.carrier.get(f"/api/carrier/cancel-applications/{application['id']}", headers=f.carrier_headers)
    assert detail.status_code == 200, detail.text
    listed = _carrier_list(f.carrier, f.carrier_headers)
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == application["id"] for item in listed.json())

    url = f"/api/carrier/cancel-applications/{application['id']}"
    assert f.carrier.put(url, headers=f.carrier_headers, json={}).status_code == 405
    assert f.carrier.patch(url, headers=f.carrier_headers, json={}).status_code == 405
    assert f.carrier.delete(url, headers=f.carrier_headers).status_code == 405
    assert f.shipper.put(
        f"/api/shipper/orders/{f.order['id']}/cancel",
        headers=f.shipper_headers,
        json={},
    ).status_code == 405


# 12. 跨主体一律 404：他人货主、他人公司、司机角色均不可访问
def test_cross_subject_access_returns_404(client):
    f = Fixture(client)
    f.accept()
    application = _apply(f.shipper, f.shipper_headers, f.order["id"], reason="越权校验").json()

    _seed_account(client, "shipper2", "货主")
    other_shipper = _client(client)
    other_headers = _login_headers(other_shipper, "shipper2")
    assert _apply(other_shipper, other_headers, f.order["id"], reason="越权").status_code == 404
    assert _view(other_shipper, other_headers, f.order["id"]).status_code == 404
    assert _options(other_shipper, other_headers, f.order["id"]).status_code == 404

    other = Fixture(client, "carrier3")
    assert _agree(other.carrier, other.carrier_headers, application["id"]).status_code == 404
    assert _reject(other.carrier, other.carrier_headers, application["id"], "驳回").status_code == 404
    assert other.carrier.get(
        f"/api/carrier/cancel-applications/{application['id']}", headers=other.carrier_headers
    ).status_code == 404

    driver_client = _client(client)
    driver_headers = _login_headers(driver_client, "admin", "admin123456")
    assert _agree(driver_client, driver_headers, application["id"]).status_code == 404
