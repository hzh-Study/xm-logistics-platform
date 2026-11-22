"""评审修复回归测试：全部断言经 HTTP seam，数据准备可用 sqlite3。

覆盖：追加式前向指针、审核字面量、取消/异常互斥、待派单投影、
终止/同意取消释放资源、发布时冻结坐标与特殊货物门禁、本地时间。
"""

import sqlite3
from datetime import datetime

from app.config import Settings
from app.core.security import hash_password
from app.main import create_app

PASSWORD = "pw123456"
TEMP_PASSWORD = "temp123456"
NEW_PASSWORD = "new123456"
SEED_ADMIN = ("admin", "admin123456")


def _now() -> str:
    return datetime.now().isoformat()


def _db(client) -> sqlite3.Connection:
    return sqlite3.connect(client.app.state.settings.db_path)


def _seed_account(client, phone: str, role: str, *, auth_status: str = "审核通过") -> int:
    conn = _db(client)
    try:
        row = conn.execute("SELECT id FROM accounts WHERE phone = ?", (phone,)).fetchone()
        if row:
            return row[0]
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            """INSERT INTO accounts
               (phone, role, account_status, auth_status, password_hash, created_at)
               VALUES (?, ?, '正常使用', ?, ?, ?)""",
            (phone, role, auth_status, hash_password(PASSWORD), _now()),
        )
        account_id = cur.lastrowid
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


def _login(client, phone: str, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"phone": phone, "password": password})


def _csrf(resp) -> dict:
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _headers(client, phone: str, password: str = PASSWORD) -> dict:
    return _csrf(_login(client, phone, password))


def _client(app_client):
    return type(app_client)(app_client.app)


def _publish(client, headers: dict, **overrides):
    body = {
        "cargo_name": "冷轧钢板",
        "cargo_type": "钢材",
        "weight": "50000 kg",
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


class Fixture:
    """货主 + 物流公司 + 已承接订单；按需创建司机/车辆/任务。"""

    def __init__(self, client, carrier_phone: str = "rv-carrier", shipper_phone: str = "rv-shipper"):
        self.app = client
        self.carrier_id = _seed_account(client, carrier_phone, "物流公司")
        _seed_account(client, shipper_phone, "货主")
        self.shipper = client
        self.shipper_headers = _headers(client, shipper_phone)
        self.carrier = _client(client)
        self.carrier_headers = _headers(self.carrier, carrier_phone)
        published = _publish(self.shipper, self.shipper_headers)
        assert published.status_code == 201, published.text
        accepted = self.carrier.post(
            f"/api/carrier/order-pool/{published.json()['id']}/accept",
            headers=self.carrier_headers,
        )
        assert accepted.status_code == 200, accepted.text
        self.order = accepted.json()

    def driver(self, phone: str):
        created = self.carrier.post(
            "/api/carrier/drivers",
            headers=self.carrier_headers,
            json={"phone": phone, "password": TEMP_PASSWORD, "name": "司机"},
        )
        assert created.status_code == 201, created.text
        drv = _client(self.app)
        login = _login(drv, phone, TEMP_PASSWORD)
        assert login.status_code == 200, login.text
        h = _csrf(login)
        assert drv.post("/api/driver/change-password", headers=h,
                        json={"new_password": NEW_PASSWORD}).status_code == 204
        bound = drv.post(
            "/api/driver/binding",
            headers=h,
            json={
                "name": "司机",
                "id_number": "110101199001011234",
                "license_no": "LIC-2026-001",
                "license_type": "B2",
                "license_expiry": "2030-01-01",
            },
        )
        assert bound.status_code == 200, bound.text
        return created.json(), drv, _headers(drv, phone, NEW_PASSWORD)

    def vehicle(self, plate: str):
        created = self.carrier.post(
            "/api/carrier/vehicles",
            headers=self.carrier_headers,
            json={
                "plate_no": plate,
                "vehicle_type": "平板货车",
                "length_m": 13.0,
                "max_load_kg": 30000,
                "owner_type": "公司",
                "document_status": "有效",
            },
        )
        assert created.status_code == 201, created.text
        return created.json()

    def task(self, phone: str, plate: str, *, accept: bool = True, start: bool = False):
        info, drv, headers = self.driver(phone)
        vehicle = self.vehicle(plate)
        created = self.carrier.post(
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
        assert created.status_code == 201, created.text
        task = created.json()
        if accept:
            assert drv.post(f"/api/driver/tasks/{task['id']}/accept", headers=headers).status_code == 200
        if start:
            self._make_in_transit(drv, headers, task["id"])
        return task, drv, headers, info, vehicle

    def _make_in_transit(self, drv, headers, task_id: int) -> None:
        assert drv.post(
            f"/api/driver/tasks/{task_id}/checkin",
            headers=headers,
            json={
                "latitude": 31.2, "longitude": 121.5,
                "arrived_at": "2026-11-23T09:55:00+00:00",
                "photos": ["v/checkin.jpg"], "notes": "已到",
            },
        ).status_code == 201
        for phase in ("装货前", "装货中", "装货完成"):
            assert drv.post(
                f"/api/driver/tasks/{task_id}/loading/photos",
                headers=headers,
                json={"phase": phase, "paths": [f"v/{phase}.jpg"]},
            ).status_code == 201
        assert drv.post(
            f"/api/driver/tasks/{task_id}/start-transport",
            headers=headers,
            json={"cargo_confirmed": True, "vehicle_confirmed": True, "notes": "核对无误"},
        ).status_code == 200

    def admin(self):
        admin = _client(self.app)
        return admin, _headers(admin, *SEED_ADMIN)

    def order_status(self) -> str:
        resp = self.shipper.get(f"/api/shipper/orders/{self.order['id']}")
        assert resp.status_code == 200, resp.text
        return resp.json()["status"]


# 1. 追加式前向指针：重新提交后旧记录指向新记录，当前记录 replaced_by 为空
def test_carrier_resubmission_uses_forward_pointer(client):
    f = Fixture(client, "rv-ptr-carrier", "rv-ptr-shipper")
    login = _login(f.carrier, "rv-ptr-carrier")
    submit = {
        "company_name": "旧公司名", "license_no": "L1", "license_path": "v/l1.pdf",
        "legal_person": "张总", "contact_name": "李联系", "contact_phone": "13800000001",
        "qualification_path": "v/q1.pdf", "note": "首次",
    }
    assert f.carrier.post("/api/carrier/certification", headers=_csrf(login), json=submit).status_code == 201
    submit["company_name"] = "新公司名"
    submit["note"] = "重新提交"
    assert f.carrier.post("/api/carrier/certification", headers=_csrf(login), json=submit).status_code == 201
    records = f.carrier.get("/api/carrier/certification").json()["records"]
    assert len(records) == 2
    assert records[0]["replaced_by"] == records[1]["id"]
    assert records[1]["replaced_by"] is None
    # 管理端统一视图读到的是当前提交（新公司名）
    admin, admin_headers = f.admin()
    items = admin.get("/api/admin/certifications?category=企业", headers=admin_headers).json()
    item = next(i for i in items if i["subject_id"] == f.carrier_id)
    assert item["subject_name"] == "新公司名"


# 2. 审核结论对外统一 审核通过 / 审核不通过，统一审核入口复用同一词汇
def test_unified_review_uses_canonical_decision_vocabulary(client):
    f = Fixture(client, "rv-dec-carrier", "rv-dec-shipper")
    login = _login(f.carrier, "rv-dec-carrier")
    cert = f.carrier.post(
        "/api/carrier/certification",
        headers=_csrf(login),
        json={
            "company_name": "合规物流", "license_no": "L2", "license_path": "v/l2.pdf",
            "legal_person": "王总", "contact_name": "赵联系", "contact_phone": "13800000002",
            "qualification_path": "v/q2.pdf", "note": "",
        },
    ).json()
    admin, admin_headers = f.admin()
    reviewed = admin.post(
        "/api/admin/certifications/review",
        headers=admin_headers,
        json={
            "category": "企业", "target_id": f.carrier_id,
            "decision": "审核不通过", "reason": "资质文件不清晰",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["decision"] == "审核不通过"
    latest = f.carrier.get("/api/carrier/certification").json()["latest"]
    assert latest["decision"] == "审核不通过"
    assert latest["reason"] == "资质文件不清晰"
    assert cert["decision"] == ""


# 3. 取消申请待公司处理时，司机上报异常返回 409 而非 500，订单状态不变
def test_anomaly_blocked_while_cancel_application_pending(client):
    f = Fixture(client, "rv-exc-carrier", "rv-exc-shipper")
    task, drv, headers, _, _ = f.task("rv-exc-driver", "京RV00001")
    applied = f.shipper.post(
        f"/api/shipper/orders/{f.order['id']}/cancel",
        headers=f.shipper_headers,
        json={"reason": "货主改计划"},
    )
    assert applied.status_code == 201, applied.text
    assert f.order_status() == "取消处理中"
    resp = drv.post(
        f"/api/driver/tasks/{task['id']}/anomalies",
        headers=headers,
        json={
            "kind": "故障", "detail": "发动机异响", "photos": ["v/exc.jpg"],
            "occurred_at": "2026-11-23T10:30:00+00:00",
        },
    )
    assert resp.status_code == 409, resp.text
    assert "error" in resp.json()
    assert f.order_status() == "取消处理中"
    view = f.carrier.get(f"/api/carrier/tasks/{task['id']}/exceptions").json()
    assert view["anomalies"] == []


# 4. 订单已进入异常处理中时，货主取消申请返回 409（互斥的反向）
def test_cancel_blocked_while_order_in_exception_processing(client):
    f = Fixture(client, "rv-rev-carrier", "rv-rev-shipper")
    task, drv, headers, _, _ = f.task("rv-rev-driver", "京RV00002", start=True)
    anomaly = drv.post(
        f"/api/driver/tasks/{task['id']}/anomalies",
        headers=headers,
        json={
            "kind": "故障", "detail": "封路", "photos": ["v/exc.jpg"],
            "occurred_at": "2026-11-23T11:00:00+00:00",
        },
    )
    assert anomaly.status_code == 201, anomaly.text
    assert f.order_status() == "异常处理中"
    resp = f.shipper.post(
        f"/api/shipper/orders/{f.order['id']}/cancel",
        headers=f.shipper_headers,
        json={"reason": "想取消"},
    )
    assert resp.status_code == 409, resp.text
    assert f.order_status() == "异常处理中"


# 5. 司机拒绝后 DB 状态仍为已承接，读模型投影为待派单；重新派单后投影恢复
def test_driver_reject_exposes_pending_dispatch_projection(client):
    f = Fixture(client, "rv-rej-carrier", "rv-rej-shipper")
    task, drv, headers, info, vehicle = f.task("rv-rej-driver", "京RV00003", accept=False)
    rejected = drv.post(
        f"/api/driver/tasks/{task['id']}/reject",
        headers=headers,
        json={"reason": "临时有事"},
    )
    assert rejected.status_code == 200, rejected.text
    detail = f.shipper.get(f"/api/shipper/orders/{f.order['id']}").json()
    assert detail["status"] == "已承接"
    assert detail["display_status"] == "待派单"
    admin, admin_headers = f.admin()
    admin_order = admin.get(f"/api/admin/orders/{f.order['id']}", headers=admin_headers).json()
    assert admin_order["display_status"] == "待派单"

    # 司机拒绝后任务为终态，订单回到待派单：可再派发一条新任务给另一名司机
    new_driver, _, _ = f.driver("rv-rej-driver2")
    new_vehicle = f.vehicle("京RV00004")
    redispatched = f.carrier.post(
        "/api/carrier/tasks",
        headers=f.carrier_headers,
        json={
            "order_id": f.order["id"],
            "driver_account_id": new_driver["account_id"],
            "vehicle_id": new_vehicle["id"],
            "planned_load_at": "2026-11-23T10:00:00+00:00",
            "planned_deliver_at": "2026-11-24T10:00:00+00:00",
            "notes": "原司机拒绝后改派",
        },
    )
    assert redispatched.status_code == 201, redispatched.text
    detail = f.shipper.get(f"/api/shipper/orders/{f.order['id']}").json()
    assert detail["display_status"] == "已承接"


# 6. 终止运输后释放司机与车辆占用：车辆可转籍、司机恢复可派单
def test_terminate_transport_releases_resources(client):
    f = Fixture(client, "rv-term-carrier", "rv-term-shipper")
    task, drv, headers, info, vehicle = f.task("rv-term-driver", "京RV00005", start=True)
    anomaly = drv.post(
        f"/api/driver/tasks/{task['id']}/anomalies",
        headers=headers,
        json={
            "kind": "事故", "detail": "车辆报废", "photos": ["v/exc.jpg"],
            "occurred_at": "2026-11-23T12:00:00+00:00",
        },
    ).json()
    handled = f.carrier.post(
        f"/api/carrier/tasks/{task['id']}/exceptions/{anomaly['id']}/handle",
        headers=f.carrier_headers,
        json={"result": "终止运输", "detail": "车辆报废，无法继续"},
    )
    assert handled.status_code == 201, handled.text
    assert f.order_status() == "已取消"
    admin, admin_headers = f.admin()
    drivers = admin.get("/api/admin/drivers", headers=admin_headers).json()
    assert next(d for d in drivers if d["account_id"] == info["account_id"])["availability"] == "可派单"
    vehicles = admin.get("/api/admin/vehicles", headers=admin_headers).json()
    assert next(v for v in vehicles if v["id"] == vehicle["id"])["availability"] == "可用"

    target = _seed_account(f.app, "rv-term-target", "物流公司")
    transfer = admin.post(
        "/api/admin/vehicle-transfers",
        headers=admin_headers,
        json={"vehicle_id": vehicle["id"], "to_carrier_id": target, "reason": "终止后转籍"},
    )
    assert transfer.status_code == 201, transfer.text


# 7. 公司同意取消后同样释放司机与车辆占用
def test_agree_cancel_releases_resources(client):
    f = Fixture(client, "rv-agree-carrier", "rv-agree-shipper")
    task, drv, headers, info, vehicle = f.task("rv-agree-driver", "京RV00006")
    applied = f.shipper.post(
        f"/api/shipper/orders/{f.order['id']}/cancel",
        headers=f.shipper_headers,
        json={"reason": "计划变更"},
    )
    assert applied.status_code == 201, applied.text
    agreed = f.carrier.post(
        f"/api/carrier/cancel-applications/{applied.json()['id']}/agree",
        headers=f.carrier_headers,
    )
    assert agreed.status_code == 200, agreed.text
    assert f.order_status() == "已取消"
    admin, admin_headers = f.admin()
    drivers = admin.get("/api/admin/drivers", headers=admin_headers).json()
    assert next(d for d in drivers if d["account_id"] == info["account_id"])["availability"] == "可派单"
    vehicles = admin.get("/api/admin/vehicles", headers=admin_headers).json()
    assert next(v for v in vehicles if v["id"] == vehicle["id"])["availability"] == "可用"


# 8. 发布时冻结收发坐标，遗留补录端点不得重写已固化快照
def test_publish_freezes_coordinates_and_blocks_rewrite(client):
    shipper_id = _seed_account(client, "rv-coord-shipper", "货主")
    headers = _headers(client, "rv-coord-shipper")
    published = _publish(
        client,
        headers,
        shipping_latitude=31.2,
        shipping_longitude=121.5,
        receiving_latitude=31.28,
        receiving_longitude=120.62,
    )
    assert published.status_code == 201, published.text
    order = published.json()
    assert order["shipping_snapshot"]["latitude"] == 31.2
    assert order["shipping_snapshot"]["longitude"] == 121.5
    assert order["receiving_snapshot"]["latitude"] == 31.28

    locked = client.post(
        f"/api/shipper/orders/{order['id']}/site-coordinate",
        headers=headers,
        json={"latitude": 39.9, "longitude": 116.4},
    )
    assert locked.status_code == 409, locked.text
    detail = client.get(f"/api/shipper/orders/{order['id']}").json()
    assert detail["shipping_snapshot"]["latitude"] == 31.2


# 9. 冻结坐标真正驱动超范围告警
def test_out_of_range_warning_uses_frozen_snapshot(client):
    f = Fixture(client, "rv-warn-carrier", "rv-warn-shipper")
    # 在已承接订单上按新契约补录一次坐标（发布未携带时允许一次）
    assert f.shipper.post(
        f"/api/shipper/orders/{f.order['id']}/site-coordinate",
        headers=f.shipper_headers,
        json={"latitude": 31.2, "longitude": 121.5},
    ).status_code == 200
    task, drv, headers, _, _ = f.task("rv-warn-driver", "京RV00007")
    far = drv.post(
        f"/api/driver/tasks/{task['id']}/checkin",
        headers=headers,
        json={
            "latitude": 39.9, "longitude": 116.4,
            "arrived_at": "2026-11-23T09:55:00+00:00",
            "photos": ["v/checkin.jpg"], "notes": "位置异常",
        },
    )
    assert far.status_code == 201, far.text
    assert far.json()["position_status"] == "位置异常"
    assert far.json()["exception_note_required"] is True
    assert far.json()["warning"]


# 10. 特殊货物发布门禁：缺运输要求或资质信息均被拒绝
def test_special_cargo_requires_requirements_and_qualification(client):
    _seed_account(client, "rv-cargo-shipper", "货主")
    headers = _headers(client, "rv-cargo-shipper")
    missing = _publish(client, headers, cargo_type="危险品-工业级")
    assert missing.status_code == 422, missing.text
    message = str(missing.json()["error"]["details"])
    assert "运输要求" in message
    assert "资质信息" in message

    ok = _publish(
        client,
        headers,
        cargo_type="危险品-工业级",
        transport_remarks="需防爆车厢与押运员",
        special_cargo_qualification="危化品道路运输许可证 RFC-2026-01",
    )
    assert ok.status_code == 201, ok.text
    detail = client.get(f"/api/shipper/orders/{ok.json()['id']}").json()
    assert detail["special_cargo_qualification"] == "危化品道路运输许可证 RFC-2026-01"


# 11. 时间戳为本地 naive ISO 8601（不含 UTC 偏移后缀）
def test_timestamps_are_local_naive_iso8601(client):
    _seed_account(client, "rv-time-shipper", "货主")
    headers = _headers(client, "rv-time-shipper")
    published = _publish(client, headers)
    assert published.status_code == 201, published.text
    created_at = published.json()["created_at"]
    parsed = datetime.fromisoformat(created_at)
    assert parsed.tzinfo is None, created_at
