"""发货地打卡、装货与起运 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。

覆盖打卡定位/超范围告警/异常说明、装货照片与异常、起运门禁与状态推进、
公司与货主进度查看、关键节点通知、跨主体 404 与司机端无运费报价。
"""

import math
import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.core.security import hash_password
from app.main import create_app

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


def _client(client: TestClient) -> TestClient:
    return TestClient(client.app)


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


class Fixture:
    """完整链路夹具：货主 + 物流公司 + 已承接订单 + 已确认待装货任务。"""

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

    def driver(self, phone: str) -> tuple[dict, TestClient, dict]:
        info = _create_driver(self.carrier, self.carrier_headers, phone)
        drv = _onboard_driver(self.app, phone)
        return info, drv, _driver_headers(drv, phone)

    def vehicle(self, plate: str) -> dict:
        return _create_vehicle(self.carrier, self.carrier_headers, plate)

    def task(self, phone: str, plate: str, *, accept: bool = True) -> tuple[dict, TestClient, dict]:
        driver, drv, headers = self.driver(phone)
        vehicle = self.vehicle(plate)
        dispatched = self.carrier.post(
            "/api/carrier/tasks",
            headers=self.carrier_headers,
            json={
                "order_id": self.order["id"],
                "driver_account_id": driver["account_id"],
                "vehicle_id": vehicle["id"],
                "planned_load_at": "2026-11-23T10:00:00+00:00",
                "planned_deliver_at": "2026-11-23T12:00:00+00:00",
                "notes": "注意防潮",
            },
        )
        assert dispatched.status_code == 201, dispatched.text
        task = dispatched.json()
        if accept:
            done = drv.post(
                f"/api/driver/tasks/{task['id']}/accept", headers=headers
            )
            assert done.status_code == 200, done.text
        return task, drv, headers

    def set_site(self, lat: float, lon: float) -> None:
        resp = self.shipper.post(
            f"/api/shipper/orders/{self.order['id']}/site-coordinate",
            headers=self.shipper_headers,
            json={"latitude": lat, "longitude": lon},
        )
        assert resp.status_code == 200, resp.text


def _driver_headers(drv: TestClient, phone: str) -> dict:
    return _csrf(_login(drv, phone, NEW_PASSWORD))


def _checkin(
    drv: TestClient,
    headers: dict,
    task_id: int,
    *,
    lat: float = 31.2000,
    lon: float = 121.5000,
    arrived_at: str = "2026-11-23T09:55:00+00:00",
    photos: list[str] | None = None,
    notes: str = "已到发货点",
):
    return drv.post(
        f"/api/driver/tasks/{task_id}/checkin",
        headers=headers,
        json={
            "latitude": lat,
            "longitude": lon,
            "arrived_at": arrived_at,
            "photos": photos if photos is not None else ["vouchers/checkin/site.jpg"],
            "notes": notes,
        },
    )


def _all_loading(drv: TestClient, headers: dict, task_id: int) -> None:
    for phase in ("装货前", "装货中", "装货完成"):
        resp = drv.post(
            f"/api/driver/tasks/{task_id}/loading/photos",
            headers=headers,
            json={"phase": phase, "paths": [f"vouchers/loading/{phase}.jpg"]},
        )
        assert resp.status_code == 201, resp.text


def _start(
    drv: TestClient,
    headers: dict,
    task_id: int,
    *,
    cargo: bool = True,
    vehicle: bool = True,
):
    return drv.post(
        f"/api/driver/tasks/{task_id}/start-transport",
        headers=headers,
        json={
            "cargo_confirmed": cargo,
            "vehicle_confirmed": vehicle,
            "notes": "货物与车辆核对无误",
        },
    )


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# 1. 发货地打卡：定位、时间、现场照片与备注落库，公司与货主进度可见
def test_departure_checkin_records_location_time_photo_notes(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-checkin", "京A00001")

    resp = _checkin(drv, headers, task["id"])
    assert resp.status_code == 201, resp.text
    checkin = resp.json()
    assert checkin["task_id"] == task["id"]
    assert checkin["task_no"] == task["task_no"]
    assert checkin["latitude"] == 31.2
    assert checkin["longitude"] == 121.5
    assert checkin["arrived_at"] == "2026-11-23T09:55:00+00:00"
    assert checkin["photos"] == ["vouchers/checkin/site.jpg"]
    assert checkin["notes"] == "已到发货点"
    assert checkin["position_status"] == "正常"
    assert checkin["exception_note_required"] is False

    carrier_progress = f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").json()
    assert len(carrier_progress["checkins"]) == 1
    assert carrier_progress["checkins"][0]["photos"] == ["vouchers/checkin/site.jpg"]
    shipper_progress = f.shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").json()
    assert len(shipper_progress["checkins"]) == 1
    assert shipper_progress["task_status"] == "待装货"


# 2. 超范围打卡：返回位置异常告警而非驳回，可提交异常说明
def test_out_of_range_checkin_warns_without_rejecting(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-far", "京A00002")
    f.set_site(31.2000, 121.5000)

    resp = _checkin(drv, headers, task["id"], lat=31.2600, lon=121.5000)
    assert resp.status_code == 201, resp.text
    checkin = resp.json()
    assert checkin["position_status"] == "位置异常"
    assert checkin["exception_note_required"] is True
    assert checkin["warning"]
    assert _haversine_m(31.26, 121.5, 31.2, 121.5) > 1000
    assert checkin["distance_m"] > 1000

    note = drv.post(
        f"/api/driver/tasks/{task['id']}/checkin/exception-note",
        headers=headers,
        json={"note": "导航引导至侧门，实际为同一厂区"},
    )
    assert note.status_code == 201, note.text
    assert note.json()["note"] == "导航引导至侧门，实际为同一厂区"

    progress = f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").json()
    assert progress["checkins"][0]["position_status"] == "位置异常"
    assert any(n["note"] == "导航引导至侧门，实际为同一厂区" for n in progress["exception_notes"])


# 3. 装货前 / 中 / 完成照片与数量不符 / 货损 / 超载异常均落库且双方可见
def test_loading_photos_and_anomalies_recorded(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-load", "京A00003")
    _all_loading(drv, headers, task["id"])

    made = drv.post(
        f"/api/driver/tasks/{task['id']}/loading/anomalies",
        headers=headers,
        json={
            "kind": "数量不符",
            "detail": "实装 48 吨，少于单据 50 吨",
            "photos": ["vouchers/loading/short.jpg"],
        },
    )
    assert made.status_code == 201, made.text
    assert made.json()["kind"] == "数量不符"

    for kind in ("货损", "超载"):
        r = drv.post(
            f"/api/driver/tasks/{task['id']}/loading/anomalies",
            headers=headers,
            json={"kind": kind, "detail": f"{kind}记录"},
        )
        assert r.status_code == 201, r.text

    progress = f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").json()
    assert {p["phase"] for p in progress["loading_photos"]} == {"装货前", "装货中", "装货完成"}
    assert len(progress["loading_anomalies"]) == 3
    shipper_progress = f.shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").json()
    assert len(shipper_progress["loading_photos"]) == 3
    assert {a["kind"] for a in shipper_progress["loading_anomalies"]} == {
        "数量不符",
        "货损",
        "超载",
    }


# 4. 起运门禁：打卡、异常说明、装货照片、车辆货物确认缺一不可
def test_start_transport_blocked_until_all_prerequisites_done(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-gate", "京A00004")
    task_id = task["id"]

    # 无打卡 → 409
    assert _start(drv, headers, task_id).status_code == 409
    # 有打卡但无装货照片 → 409
    assert _checkin(drv, headers, task_id).status_code == 201
    assert _start(drv, headers, task_id).status_code == 409
    # 装货照片齐但无确认标记 → 409
    _all_loading(drv, headers, task_id)
    assert _start(drv, headers, task_id, cargo=False, vehicle=True).status_code == 409
    assert _start(drv, headers, task_id, cargo=True, vehicle=False).status_code == 409
    # 确认齐备 → 200
    ok = _start(drv, headers, task_id)
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "运输中"


# 5. 起运前位置异常必须提交异常说明，否则禁止起运
def test_out_of_range_requires_exception_note_before_start(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-gate-far", "京A00005")
    task_id = task["id"]
    f.set_site(31.2000, 121.5000)
    assert _checkin(drv, headers, task_id, lat=31.2600).status_code == 201
    _all_loading(drv, headers, task_id)

    blocked = _start(drv, headers, task_id)
    assert blocked.status_code == 409
    assert "异常说明" in blocked.json()["error"]["message"]

    note = drv.post(
        f"/api/driver/tasks/{task_id}/checkin/exception-note",
        headers=headers,
        json={"note": "厂区较大，门岗定位与装货点有偏差"},
    )
    assert note.status_code == 201, note.text
    assert _start(drv, headers, task_id).status_code == 200


# 6. 起运成功：任务与订单同时转运输中，关键节点通知按收件人规则落库
def test_start_transport_advances_statuses_and_notifies(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-start", "京A00006")
    task_id = task["id"]
    assert _checkin(drv, headers, task_id).status_code == 201
    _all_loading(drv, headers, task_id)

    started = _start(drv, headers, task_id)
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "运输中"

    carrier_task = f.carrier.get(f"/api/carrier/tasks/{task_id}").json()
    assert carrier_task["status"] == "运输中"
    order = f.shipper.get(f"/api/shipper/orders/{f.order['id']}").json()
    assert order["status"] == "运输中"

    driver_notes = drv.get("/api/driver/notifications").json()
    carrier_notes = f.carrier.get("/api/carrier/notifications").json()
    shipper_notes = f.shipper.get("/api/shipper/notifications").json()
    assert any(n["kind"] == "开始运输" and n["related_id"] == task_id for n in driver_notes)
    assert any(n["kind"] == "开始运输" and n["related_id"] == task_id for n in carrier_notes)
    assert any(n["kind"] == "开始运输" and n["related_id"] == task_id for n in shipper_notes)
    assert any("打卡" in n["kind"] for n in carrier_notes)
    assert any("打卡" in n["kind"] for n in shipper_notes)


# 7. 跨主体访问一律 404：司机任务、公司任务、货主订单互不越界
def test_cross_subject_access_returns_404(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-mine", "京A00007")
    other_f = Fixture(client, "carrier-other")
    other_task, other_drv, other_headers = other_f.task("driver-other", "京B00007")

    # 正向对照：本人 / 本公司 / 本货主可访问
    assert drv.get(f"/api/driver/tasks/{task['id']}/progress").status_code == 200
    assert f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").status_code == 200
    assert f.shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").status_code == 200

    # 反向：跨主体一律 404
    assert _checkin(other_drv, other_headers, task["id"]).status_code == 404
    assert other_drv.get(f"/api/driver/tasks/{task['id']}/progress").status_code == 404
    assert other_f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").status_code == 404
    assert f.carrier.get(f"/api/carrier/tasks/{other_task['id']}/progress").status_code == 404

    _seed_account(client, "shipper-other", "货主")
    other_shipper = _client(client)
    _login_headers(other_shipper, "shipper-other")
    assert other_shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").status_code == 404


# 8. 司机端进度出参不含运费报价
def test_driver_progress_has_no_quote_fields(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-noquote", "京A00008")
    _checkin(drv, headers, task["id"])

    progress = drv.get(f"/api/driver/tasks/{task['id']}/progress").json()
    assert not any(key.startswith("quote") for key in progress)
    assert "quote_amount_yuan" not in progress
    assert progress["task_no"] == task["task_no"]


# 9. 打卡半径可配置：同一超范围距离在更大半径下视为正常
def test_checkin_radius_is_configurable(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "wide.db"),
        data_dir=str(tmp_path / "data"),
        cookie_secure=False,
        seed_admin_phone="admin",
        seed_admin_password="admin123456",
        checkin_radius_m=10000,
    )
    with TestClient(create_app(settings)) as client:
        f = Fixture(client)
        task, drv, headers = f.task("driver-wide", "京A00009")
        f.set_site(31.2000, 121.5000)
        resp = _checkin(drv, headers, task["id"], lat=31.2600)
        assert resp.status_code == 201, resp.text
        assert resp.json()["position_status"] == "正常"
        assert resp.json()["exception_note_required"] is False
