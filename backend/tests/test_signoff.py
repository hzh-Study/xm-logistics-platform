"""收货地打卡、卸货与签收完成 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。

覆盖收货打卡定位/超范围告警/异常说明、卸货照片与异常、签收资料提交、
公司确认后任务与订单状态推进、货主只读、关键节点通知、凭证留档、
跨主体 404 与司机端无运费报价。
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
            (phone, role, "正常使用", auth_status, hash_password(PASSWORD), _now()),
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
    """完整链路夹具：货主 + 物流公司 + 已承接订单 + 运输中任务。"""

    def __init__(self, client: TestClient, carrier_phone: str = "carrier1", *, start: bool = True):
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
            done = drv.post(f"/api/driver/tasks/{task['id']}/accept", headers=headers)
            assert done.status_code == 200, done.text
        return task, drv, headers

    def set_recv_site(self, lat: float, lon: float) -> None:
        resp = self.shipper.post(
            f"/api/shipper/orders/{self.order['id']}/receiving-coordinate",
            headers=self.shipper_headers,
            json={"latitude": lat, "longitude": lon},
        )
        assert resp.status_code == 200, resp.text

    def in_transit(self, task: dict, drv: TestClient, headers: dict) -> None:
        """走完发货打卡 + 装货 + 起运，把任务推进到运输中。"""
        task_id = task["id"]
        checkin = drv.post(
            f"/api/driver/tasks/{task_id}/checkin",
            headers=headers,
            json={
                "latitude": 31.2000,
                "longitude": 121.5000,
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
            json={
                "cargo_confirmed": True,
                "vehicle_confirmed": True,
                "notes": "货物与车辆核对无误",
            },
        )
        assert started.status_code == 200, started.text
        assert started.json()["status"] == "运输中"


def _driver_headers(drv: TestClient, phone: str) -> dict:
    return _csrf(_login(drv, phone, NEW_PASSWORD))


def _arrival_checkin(
    drv: TestClient,
    headers: dict,
    task_id: int,
    *,
    lat: float = 31.2800,
    lon: float = 120.6200,
    arrived_at: str = "2026-11-23T11:55:00+00:00",
    photos: list[str] | None = None,
    notes: str = "已到收货点",
):
    return drv.post(
        f"/api/driver/tasks/{task_id}/arrival-checkin",
        headers=headers,
        json={
            "latitude": lat,
            "longitude": lon,
            "arrived_at": arrived_at,
            "photos": photos if photos is not None else ["vouchers/arrival/site.jpg"],
            "notes": notes,
        },
    )


def _all_unloading(drv: TestClient, headers: dict, task_id: int) -> None:
    for phase in ("卸货前", "卸货中", "卸货完成"):
        resp = drv.post(
            f"/api/driver/tasks/{task_id}/unloading/photos",
            headers=headers,
            json={"phase": phase, "paths": [f"vouchers/unloading/{phase}.jpg"]},
        )
        assert resp.status_code == 201, resp.text


def _signoff(
    drv: TestClient,
    headers: dict,
    task_id: int,
    *,
    condition: str = "完好",
    received_at: str = "2026-11-23T12:20:00+00:00",
    receiver: str = "李收货",
    **overrides,
):
    body = {
        "receiving_condition": condition,
        "received_at": received_at,
        "receiver_name": receiver,
        "signature_photos": ["vouchers/signoff/signature.jpg"],
        "vouchers": ["vouchers/signoff/receipt.jpg"],
        "notes": "签收无误",
    }
    body.update(overrides)
    return drv.post(f"/api/driver/tasks/{task_id}/signoff", headers=headers, json=body)


def _confirm(carrier: TestClient, headers: dict, task_id: int, *, confirmed: bool = True):
    return carrier.post(
        f"/api/carrier/tasks/{task_id}/signoff/confirm",
        headers=headers,
        json={"confirmed": confirmed, "notes": "凭证齐全，确认完成"},
    )


# 1. 收货地打卡：定位、时间、现场照片与备注落库，公司与货主进度可见，任务转待签收
def test_arrival_checkin_records_location_time_photo_notes(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-arrival", "京A10001")
    f.set_recv_site(31.2800, 120.6200)
    f.in_transit(task, drv, headers)

    resp = _arrival_checkin(drv, headers, task["id"])
    assert resp.status_code == 201, resp.text
    checkin = resp.json()
    assert checkin["task_id"] == task["id"]
    assert checkin["latitude"] == 31.28
    assert checkin["longitude"] == 120.62
    assert checkin["arrived_at"] == "2026-11-23T11:55:00+00:00"
    assert checkin["photos"] == ["vouchers/arrival/site.jpg"]
    assert checkin["notes"] == "已到收货点"
    assert checkin["position_status"] == "正常"
    assert checkin["exception_note_required"] is False

    carrier_progress = f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").json()
    assert len(carrier_progress["arrival_checkins"]) == 1
    assert carrier_progress["task_status"] == "待签收"
    shipper_progress = f.shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").json()
    assert len(shipper_progress["arrival_checkins"]) == 1


# 2. 超范围收货打卡：返回位置异常告警而非驳回，可提交异常说明
def test_out_of_range_arrival_checkin_warns_and_allows_note(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-arrival-far", "京A10002")
    f.set_recv_site(31.2800, 120.6200)
    f.in_transit(task, drv, headers)

    resp = _arrival_checkin(drv, headers, task["id"], lat=31.3500)
    assert resp.status_code == 201, resp.text
    checkin = resp.json()
    assert checkin["position_status"] == "位置异常"
    assert checkin["exception_note_required"] is True
    assert checkin["warning"]
    assert checkin["distance_m"] > 1000

    note = drv.post(
        f"/api/driver/tasks/{task['id']}/arrival-checkin/exception-note",
        headers=headers,
        json={"note": "收货厂区较大，门岗定位与卸货点有偏差"},
    )
    assert note.status_code == 201, note.text
    progress = f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").json()
    assert any(n["note"] == "收货厂区较大，门岗定位与卸货点有偏差" for n in progress["arrival_notes"])


# 3. 卸货前 / 中 / 完成照片与货损 / 数量不符 / 拒收异常均落库且双方可见
def test_unloading_photos_and_anomalies_recorded(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-unload", "京A10003")
    f.in_transit(task, drv, headers)
    _all_unloading(drv, headers, task["id"])

    made = drv.post(
        f"/api/driver/tasks/{task['id']}/unloading/anomalies",
        headers=headers,
        json={"kind": "数量不符", "detail": "实收 48 吨，少于单据 50 吨",
              "photos": ["vouchers/unloading/short.jpg"]},
    )
    assert made.status_code == 201, made.text
    assert made.json()["kind"] == "数量不符"
    for kind in ("货损", "拒收"):
        r = drv.post(
            f"/api/driver/tasks/{task['id']}/unloading/anomalies",
            headers=headers,
            json={"kind": kind, "detail": f"{kind}记录"},
        )
        assert r.status_code == 201, r.text

    progress = f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").json()
    assert {p["phase"] for p in progress["unloading_photos"]} == {"卸货前", "卸货中", "卸货完成"}
    assert {a["kind"] for a in progress["unloading_anomalies"]} == {"货损", "数量不符", "拒收"}
    shipper_progress = f.shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").json()
    assert len(shipper_progress["unloading_photos"]) == 3


# 4. 签收资料提交门禁：无到达打卡 / 无卸货照片 / 位置异常无说明均不可提交
def test_signoff_blocked_until_prerequisites_done(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-signoff-gate", "京A10004")
    f.set_recv_site(31.2800, 120.6200)
    f.in_transit(task, drv, headers)
    task_id = task["id"]

    # 无到达打卡 → 409
    assert _signoff(drv, headers, task_id).status_code == 409
    # 有打卡但无卸货照片 → 409
    assert _arrival_checkin(drv, headers, task_id).status_code == 201
    assert _signoff(drv, headers, task_id).status_code == 409
    # 卸货照片齐备 → 可提交
    _all_unloading(drv, headers, task_id)
    ok = _signoff(drv, headers, task_id)
    assert ok.status_code == 200, ok.text
    assert ok.json()["task_status"] == "待确认完成"


# 5. 位置异常必须先补说明才能提交签收资料
def test_out_of_range_requires_note_before_signoff(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-signoff-far", "京A10005")
    f.set_recv_site(31.2800, 120.6200)
    f.in_transit(task, drv, headers)
    task_id = task["id"]

    assert _arrival_checkin(drv, headers, task_id, lat=31.3500).status_code == 201
    _all_unloading(drv, headers, task_id)
    blocked = _signoff(drv, headers, task_id)
    assert blocked.status_code == 409
    assert "异常说明" in blocked.json()["error"]["message"]

    note = drv.post(
        f"/api/driver/tasks/{task_id}/arrival-checkin/exception-note",
        headers=headers,
        json={"note": "门岗与卸货区不在同一坐标"},
    )
    assert note.status_code == 201, note.text
    assert _signoff(drv, headers, task_id).status_code == 200


# 6. 签收资料提交后凭证留档，任务转待确认完成，公司可见凭证内容
def test_signoff_submission_retains_voucher(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-voucher", "京A10006")
    f.in_transit(task, drv, headers)
    task_id = task["id"]
    _arrival_checkin(drv, headers, task_id)
    _all_unloading(drv, headers, task_id)

    submitted = _signoff(drv, headers, task_id, condition="货损", receiver="王收货")
    assert submitted.status_code == 200, submitted.text
    voucher = submitted.json()["signoff_voucher"]
    assert voucher["receiving_condition"] == "货损"
    assert voucher["receiver_name"] == "王收货"
    assert voucher["signature_photos"] == ["vouchers/signoff/signature.jpg"]
    assert voucher["vouchers"] == ["vouchers/signoff/receipt.jpg"]
    assert voucher["voucher_no"].startswith("SIGN-")

    carrier_progress = f.carrier.get(f"/api/carrier/tasks/{task_id}/progress").json()
    assert carrier_progress["signoff_voucher"]["voucher_no"] == voucher["voucher_no"]
    shipper_progress = f.shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").json()
    assert shipper_progress["signoff_voucher"]["voucher_no"] == voucher["voucher_no"]


# 7. 公司确认：任务与订单同时转已完成，凭证作为完成依据保留，三方收到通知
def test_carrier_confirm_completes_task_order_and_notifies(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-complete", "京A10007")
    f.in_transit(task, drv, headers)
    task_id = task["id"]
    _arrival_checkin(drv, headers, task_id)
    _all_unloading(drv, headers, task_id)
    submitted = _signoff(drv, headers, task_id)
    assert submitted.status_code == 200, submitted.text
    voucher_no = submitted.json()["signoff_voucher"]["voucher_no"]

    confirmed = _confirm(f.carrier, f.carrier_headers, task_id)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["task_status"] == "已完成"
    assert confirmed.json()["order_status"] == "已完成"

    carrier_task = f.carrier.get(f"/api/carrier/tasks/{task_id}").json()
    assert carrier_task["status"] == "已完成"
    order = f.shipper.get(f"/api/shipper/orders/{f.order['id']}").json()
    assert order["status"] == "已完成"

    progress = f.carrier.get(f"/api/carrier/tasks/{task_id}/progress").json()
    assert progress["signoff_voucher"]["voucher_no"] == voucher_no
    assert progress["signoff_confirmation"] is not None

    driver_notes = drv.get("/api/driver/notifications").json()
    carrier_notes = f.carrier.get("/api/carrier/notifications").json()
    shipper_notes = f.shipper.get("/api/shipper/notifications").json()
    assert any(n["kind"] == "运输完成" and n["related_id"] == task_id for n in driver_notes)
    assert any(n["kind"] == "运输完成" and n["related_id"] == task_id for n in carrier_notes)
    assert any(n["kind"] == "运输完成" and n["related_id"] == task_id for n in shipper_notes)
    assert any("签收" in n["kind"] for n in carrier_notes)


# 8. 货主只读：无确认入口，确认路径 404；货主进度可见凭证但不能写
def test_shipper_is_read_only(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-shipper-read", "京A10008")
    f.in_transit(task, drv, headers)
    _arrival_checkin(drv, headers, task["id"])
    _all_unloading(drv, headers, task["id"])
    assert _signoff(drv, headers, task["id"]).status_code == 200

    # 货主没有确认入口
    resp = f.shipper.post(
        f"/api/shipper/orders/{f.order['id']}/signoff/confirm",
        headers=f.shipper_headers,
        json={"confirmed": True},
    )
    assert resp.status_code == 404
    # 货主不可代司机提交打卡 / 签收
    assert f.shipper.post(
        f"/api/driver/tasks/{task['id']}/signoff",
        headers=f.shipper_headers,
        json={"receiving_condition": "完好"},
    ).status_code == 404
    # 但货主可读凭证
    progress = f.shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").json()
    assert progress["signoff_voucher"] is not None


# 9. 跨主体访问一律 404：司机任务、公司任务、货主订单互不越界
def test_cross_subject_access_returns_404(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-mine", "京A10009")
    f.in_transit(task, drv, headers)
    other_f = Fixture(client, "carrier-other")
    other_task, other_drv, other_headers = other_f.task("driver-other", "京B10009")
    other_f.in_transit(other_task, other_drv, other_headers)

    # 正向对照
    assert drv.get(f"/api/driver/tasks/{task['id']}/progress").status_code == 200
    assert f.carrier.get(f"/api/carrier/tasks/{task['id']}/progress").status_code == 200
    assert f.shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").status_code == 200

    # 反向：跨主体一律 404
    assert _arrival_checkin(other_drv, other_headers, task["id"]).status_code == 404
    assert other_drv.get(f"/api/driver/tasks/{task['id']}/progress").status_code == 404
    assert _confirm(other_f.carrier, other_f.carrier_headers, task["id"]).status_code == 404

    _seed_account(client, "shipper-other", "货主")
    other_shipper = _client(client)
    _login_headers(other_shipper, "shipper-other")
    assert other_shipper.get(f"/api/shipper/orders/{f.order['id']}/progress").status_code == 404


# 10. 司机端进度出参不含运费报价
def test_driver_progress_has_no_quote_fields(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-noquote", "京A10010")
    f.in_transit(task, drv, headers)
    _arrival_checkin(drv, headers, task["id"])

    progress = drv.get(f"/api/driver/tasks/{task['id']}/progress").json()
    assert not any(key.startswith("quote") for key in progress)
    assert "quote_amount_yuan" not in progress
    assert progress["task_no"] == task["task_no"]


# 11. 重复确认 / 未完成订单不可确认；完成后收货快照坐标锁定
def test_completed_order_is_immutable(client):
    f = Fixture(client)
    task, drv, headers = f.task("driver-immutable", "京A10011")
    f.set_recv_site(31.2800, 120.6200)
    f.in_transit(task, drv, headers)
    task_id = task["id"]
    _arrival_checkin(drv, headers, task_id)
    _all_unloading(drv, headers, task_id)
    assert _signoff(drv, headers, task_id).status_code == 200
    assert _confirm(f.carrier, f.carrier_headers, task_id).status_code == 200

    # 再次确认 → 409
    assert _confirm(f.carrier, f.carrier_headers, task_id).status_code == 409
    # 完成后补录收货坐标 → 409
    locked = f.shipper.post(
        f"/api/shipper/orders/{f.order['id']}/receiving-coordinate",
        headers=f.shipper_headers,
        json={"latitude": 31.3, "longitude": 120.7},
    )
    assert locked.status_code == 409
