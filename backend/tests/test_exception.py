"""在途异常与换车换司机 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。

覆盖司机上报异常与现场照片、公司追加处理记录（actor/结果/时间）、换车换司机
保留前后记录且不覆盖打卡与照片、处理结果映射订单状态、终止运输置已取消、
记录只读、跨主体 404 与司机端无运费报价。
"""

import sqlite3
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.security import hash_password
from app.main import create_app

PASSWORD = "pw123456"
TEMP_PASSWORD = "temp123456"
NEW_PASSWORD = "new123456"
ISO_DT = "2026-11-24T09:30:00+00:00"


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
    """完整链路夹具：货主 + 物流公司 + 已承接订单 + 运输任务。"""

    def __init__(self, client: TestClient, carrier_phone: str = "carrier1"):
        self.app = client
        self.carrier_id = _seed_account(client, carrier_phone, "物流公司")
        _seed_account(client, "shipper1", "货主")
        self.shipper = client
        self.shipper_headers = _login_headers(client, "shipper1")
        self.carrier = _client(client)
        self.carrier_headers = _login_headers(self.carrier, carrier_phone)
        published = _publish(self.shipper, self.shipper_headers)
        assert published.status_code == 201, published.text
        accepted = self.carrier.post(
            f"/api/carrier/order-pool/{published.json()['id']}/accept",
            headers=self.carrier_headers,
        )
        assert accepted.status_code == 200, accepted.text
        self.order = accepted.json()

    def spare_driver(self, phone: str) -> tuple[dict, dict]:
        info = _create_driver(self.carrier, self.carrier_headers, phone, "备用司机")
        _onboard_driver(self.app, phone)
        return info, {}

    def spare_vehicle(self, plate: str) -> dict:
        return _create_vehicle(self.carrier, self.carrier_headers, plate)

    def task(
        self,
        phone: str,
        plate: str,
        *,
        start: bool = False,
    ) -> tuple[dict, TestClient, dict]:
        info = _create_driver(self.carrier, self.carrier_headers, phone)
        drv = _onboard_driver(self.app, phone)
        headers = _driver_headers(drv, phone)
        vehicle = _create_vehicle(self.carrier, self.carrier_headers, plate)
        dispatched = self.carrier.post(
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
        assert dispatched.status_code == 201, dispatched.text
        task = dispatched.json()
        accepted = drv.post(f"/api/driver/tasks/{task['id']}/accept", headers=headers)
        assert accepted.status_code == 200, accepted.text
        if start:
            self._make_in_transit(drv, headers, task["id"])
        return task, drv, headers

    def _make_in_transit(self, drv: TestClient, headers: dict, task_id: int) -> None:
        checkin = drv.post(
            f"/api/driver/tasks/{task_id}/checkin",
            headers=headers,
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
            resp = drv.post(
                f"/api/driver/tasks/{task_id}/loading/photos",
                headers=headers,
                json={"phase": phase, "paths": [f"vouchers/loading/{phase}.jpg"]},
            )
            assert resp.status_code == 201, resp.text
        started = drv.post(
            f"/api/driver/tasks/{task_id}/start-transport",
            headers=headers,
            json={"cargo_confirmed": True, "vehicle_confirmed": True, "notes": "核对无误"},
        )
        assert started.status_code == 200, started.text


def _anomaly(
    drv: TestClient,
    headers: dict,
    task_id: int,
    *,
    kind: str = "故障",
    detail: str = "发动机异响，靠边检查",
    photos: list[str] | None = None,
    occurred_at: str = ISO_DT,
):
    return drv.post(
        f"/api/driver/tasks/{task_id}/anomalies",
        headers=headers,
        json={
            "kind": kind,
            "detail": detail,
            "photos": photos if photos is not None else ["vouchers/exc/scene1.jpg"],
            "occurred_at": occurred_at,
        },
    )


def _handle(
    carrier: TestClient,
    headers: dict,
    task_id: int,
    anomaly_id: int,
    *,
    result: str = "继续运输",
    detail: str = "已排除故障",
    **extra,
):
    body = {"result": result, "detail": detail}
    body.update(extra)
    return carrier.post(
        f"/api/carrier/tasks/{task_id}/exceptions/{anomaly_id}/handle",
        headers=headers,
        json=body,
    )


def _order_status(f: Fixture) -> str:
    resp = f.shipper.get(f"/api/shipper/orders/{f.order['id']}")
    assert resp.status_code == 200, resp.text
    return resp.json()["status"]


# 1. 司机提交在途异常与现场照片：任务转异常、订单转异常处理中，公司与货主可见
def test_driver_submits_in_transit_anomaly_with_photos(client):
    f = Fixture(client)
    task, drv, headers = f.task("exc-driver1", "京A01001", start=True)

    resp = _anomaly(drv, headers, task["id"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["task_id"] == task["id"]
    assert body["task_no"] == task["task_no"]
    assert body["kind"] == "故障"
    assert body["detail"] == "发动机异响，靠边检查"
    assert body["photos"] == ["vouchers/exc/scene1.jpg"]
    assert body["occurred_at"] == ISO_DT
    assert body["actor"] == "司机"

    carrier_view = f.carrier.get(f"/api/carrier/tasks/{task['id']}/exceptions")
    assert carrier_view.status_code == 200, carrier_view.text
    assert len(carrier_view.json()["anomalies"]) == 1
    assert carrier_view.json()["anomalies"][0]["photos"] == ["vouchers/exc/scene1.jpg"]

    shipper_view = f.shipper.get(f"/api/shipper/orders/{f.order['id']}/exceptions")
    assert shipper_view.status_code == 200, shipper_view.text
    assert len(shipper_view.json()["anomalies"]) == 1

    assert drv.get(f"/api/driver/tasks/{task['id']}").json()["status"] == "异常"
    assert _order_status(f) == "异常处理中"


# 2. 公司追加处理记录：带 actor 角色、处理结果、处理时间与最终状态
def test_carrier_appends_handling_record_with_actor_result_time(client):
    f = Fixture(client)
    task, drv, headers = f.task("exc-driver2", "京A01002", start=True)
    anomaly = _anomaly(drv, headers, task["id"]).json()

    handled = _handle(f.carrier, f.carrier_headers, task["id"], anomaly["id"])
    assert handled.status_code == 201, handled.text
    record = handled.json()
    assert record["result"] == "继续运输"
    assert record["actor"] == "物流公司"
    assert record["anomaly_id"] == anomaly["id"]
    assert record["handled_at"]
    assert record["order_status"] == "运输中"
    assert record["task_status"] == "运输中"

    view = f.carrier.get(f"/api/carrier/tasks/{task['id']}/exceptions").json()
    assert len(view["handling_records"]) == 1
    assert view["handling_records"][0]["result"] == "继续运输"
    assert _order_status(f) == "运输中"


# 3. 五种恢复结果均使订单回到运输中（已起运）
@pytest.mark.parametrize(
    "result",
    ["继续运输", "调整送达时间", "更换车辆", "更换司机", "重新安排运输"],
)
def test_recovery_results_return_order_to_in_transit(client, result):
    f = Fixture(client)
    task, drv, headers = f.task(f"exc-drv-{result}", f"京A02{len(result)}", start=True)
    anomaly = _anomaly(drv, headers, task["id"]).json()
    extra = {}
    if result == "调整送达时间":
        extra["adjusted_deliver_at"] = "2026-11-25T10:00:00+00:00"
    if result == "更换车辆":
        extra["new_vehicle_id"] = f.spare_vehicle(f"京A03{len(result)}")["id"]
    if result == "更换司机":
        spare, _ = f.spare_driver(f"exc-spare-{result}")
        extra["new_driver_account_id"] = spare["account_id"]

    handled = _handle(
        f.carrier, f.carrier_headers, task["id"], anomaly["id"], result=result, **extra
    )
    assert handled.status_code == 201, handled.text
    assert handled.json()["result"] == result
    assert handled.json()["order_status"] == "运输中"
    assert _order_status(f) == "运输中"


# 4. 换车换司机保留前后记录与原因，且不覆盖已有打卡与装货照片
def test_change_vehicle_and_driver_keep_before_after_and_preserve_checkins(client):
    f = Fixture(client)
    task, drv, headers = f.task("exc-driver4", "京A01004", start=True)
    before = f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").json()
    before_checkins = before["checkins"]
    before_photos = before["loading_photos"]
    original_vehicle_id = task["vehicle_id"]
    original_driver_id = task["driver_account_id"]

    anomaly1 = _anomaly(drv, headers, task["id"], kind="故障").json()
    new_vehicle = f.spare_vehicle("京A04004")
    changed_vehicle = _handle(
        f.carrier,
        f.carrier_headers,
        task["id"],
        anomaly1["id"],
        result="更换车辆",
        detail="原车需维修",
        new_vehicle_id=new_vehicle["id"],
    )
    assert changed_vehicle.status_code == 201, changed_vehicle.text
    cv = changed_vehicle.json()
    assert cv["before_vehicle_id"] == original_vehicle_id
    assert cv["after_vehicle_id"] == new_vehicle["id"]
    assert cv["reason"] == "原车需维修"
    assert cv["before_driver_account_id"] == original_driver_id
    assert cv["after_driver_account_id"] == original_driver_id

    anomaly2 = _anomaly(drv, headers, task["id"], kind="事故").json()
    spare, _ = f.spare_driver("exc-driver4-spare")
    changed_driver = _handle(
        f.carrier,
        f.carrier_headers,
        task["id"],
        anomaly2["id"],
        result="更换司机",
        detail="原司机无法继续",
        new_driver_account_id=spare["account_id"],
    )
    assert changed_driver.status_code == 201, changed_driver.text
    cd = changed_driver.json()
    assert cd["before_driver_account_id"] == original_driver_id
    assert cd["after_driver_account_id"] == spare["account_id"]
    assert cd["reason"] == "原司机无法继续"

    after = f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").json()
    assert after["checkins"] == before_checkins
    assert after["loading_photos"] == before_photos

    current = f.carrier.get(f"/api/carrier/tasks/{task['id']}").json()
    assert current["vehicle_id"] == new_vehicle["id"]
    assert current["driver_account_id"] == spare["account_id"]

    history = f.carrier.get(f"/api/carrier/tasks/{task['id']}/exceptions").json()
    assert len(history["anomalies"]) == 2
    assert len(history["handling_records"]) == 2


# 5. 终止运输：唯一将订单置已取消并写明原因的结果
def test_terminate_transport_sets_order_cancelled_with_reason(client):
    f = Fixture(client)
    task, drv, headers = f.task("exc-driver5", "京A01005", start=True)
    anomaly = _anomaly(drv, headers, task["id"], kind="事故").json()

    handled = _handle(
        f.carrier,
        f.carrier_headers,
        task["id"],
        anomaly["id"],
        result="终止运输",
        detail="车辆报废，无法继续运输",
    )
    assert handled.status_code == 201, handled.text
    assert handled.json()["result"] == "终止运输"
    assert handled.json()["order_status"] == "已取消"
    assert handled.json()["task_status"] == "已取消"

    assert _order_status(f) == "已取消"
    history = f.carrier.get(f"/api/carrier/tasks/{task['id']}/exceptions").json()
    assert history["handling_records"][0]["result"] == "终止运输"
    assert history["handling_records"][0]["reason"] == "车辆报废，无法继续运输"


# 6. 未起运异常按恢复结果回到已承接（任务待装货）
def test_not_started_anomaly_recovery_returns_order_to_accepted(client):
    f = Fixture(client)
    task, drv, headers = f.task("exc-driver6", "京A01006", start=False)
    anomaly = _anomaly(drv, headers, task["id"], kind="预计延误").json()

    handled = _handle(f.carrier, f.carrier_headers, task["id"], anomaly["id"])
    assert handled.status_code == 201, handled.text
    assert handled.json()["order_status"] == "已承接"
    assert handled.json()["task_status"] == "待装货"
    assert _order_status(f) == "已承接"


# 7. 异常处理记录只读：不存在更新端点（PUT/PATCH/DELETE 均 405）
def test_exception_records_are_read_only(client):
    f = Fixture(client)
    task, drv, headers = f.task("exc-driver7", "京A01007", start=True)
    anomaly = _anomaly(drv, headers, task["id"]).json()
    _handle(f.carrier, f.carrier_headers, task["id"], anomaly["id"])

    handle_url = f"/api/carrier/tasks/{task['id']}/exceptions/{anomaly['id']}/handle"
    assert f.carrier.put(handle_url, headers=f.carrier_headers, json={}).status_code == 405
    assert f.carrier.delete(handle_url, headers=f.carrier_headers).status_code == 405
    anomaly_url = f"/api/driver/tasks/{task['id']}/anomalies"
    assert drv.put(anomaly_url, headers=headers, json={}).status_code == 405

    view = f.carrier.get(f"/api/carrier/tasks/{task['id']}/exceptions").json()
    assert len(view["anomalies"]) == 1
    assert len(view["handling_records"]) == 1


# 8. 跨主体一律 404：司机任务、公司任务、异常归属互不越界
def test_cross_subject_access_returns_404(client):
    f = Fixture(client)
    task, drv, headers = f.task("exc-mine", "京A01008", start=True)
    anomaly = _anomaly(drv, headers, task["id"]).json()

    other = Fixture(client, "carrier-other-exc")
    other_task, other_drv, other_headers = other.task("exc-other", "京B01008", start=True)
    other_anomaly = _anomaly(other_drv, other_headers, other_task["id"]).json()

    assert _anomaly(other_drv, other_headers, task["id"]).status_code == 404
    assert drv.get(f"/api/driver/tasks/{other_task['id']}/exceptions").status_code == 404
    assert other.carrier.get(f"/api/carrier/tasks/{task['id']}/exceptions").status_code == 404
    assert _handle(
        other.carrier, other.carrier_headers, task["id"], anomaly["id"]
    ).status_code == 404
    assert _handle(
        f.carrier, f.carrier_headers, task["id"], other_anomaly["id"]
    ).status_code == 404


# 9. 司机端异常出参不含运费报价
def test_driver_exception_views_have_no_quote_fields(client):
    f = Fixture(client)
    task, drv, headers = f.task("exc-driver9", "京A01009", start=True)
    anomaly = _anomaly(drv, headers, task["id"]).json()
    _handle(f.carrier, f.carrier_headers, task["id"], anomaly["id"])

    for body in (
        anomaly,
        drv.get(f"/api/driver/tasks/{task['id']}/exceptions").json(),
    ):
        for key in body:
            assert not key.startswith("quote")
        assert "quote_amount_yuan" not in body


# 10. 可配置半径之外的独立库同样能完成异常闭环（迁移在全新库上成功）
def test_exception_flow_on_fresh_database(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "exc.db"),
        data_dir=str(tmp_path / "data"),
        cookie_secure=False,
        seed_admin_phone="admin",
        seed_admin_password="admin123456",
        checkin_radius_m=10000,
    )
    with TestClient(create_app(settings)) as client:
        f = Fixture(client)
        task, drv, headers = f.task("exc-fresh", "京A01010", start=True)
        anomaly = _anomaly(drv, headers, task["id"])
        assert anomaly.status_code == 201, anomaly.text
        handled = _handle(f.carrier, f.carrier_headers, task["id"], anomaly.json()["id"])
        assert handled.status_code == 201, handled.text
