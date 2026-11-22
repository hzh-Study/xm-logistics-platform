"""派单与司机确认 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。

覆盖派单规则、时间冲突、司机确认 / 拒绝、未起运重新派单留痕、司机端无报价与门禁。
"""

import re
import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password

CARRIER_PASSWORD = "pw123456"
SHIPPER_PASSWORD = "pw123456"
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
    """布置夹具：直接插入一个已审核账号，仅用于准备。"""
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
            (
                phone,
                role,
                account_status,
                auth_status,
                hash_password(
                    CARRIER_PASSWORD if role == "物流公司" else SHIPPER_PASSWORD
                ),
                _now(),
            ),
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


def _login(client: TestClient, phone: str, password: str = CARRIER_PASSWORD):
    return client.post("/api/auth/login", json={"phone": phone, "password": password})


def _csrf(resp) -> dict:
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _login_headers(client: TestClient, phone: str, password: str = CARRIER_PASSWORD) -> dict:
    return _csrf(_login(client, phone, password))


def _client(client: TestClient) -> TestClient:
    return TestClient(client.app)


def _driver_headers(drv: TestClient, phone: str) -> dict:
    """司机改密后重新登录，取得写操作所需的 CSRF 头。"""
    return _csrf(_login(drv, phone, NEW_PASSWORD))


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


def _create_driver(client: TestClient, csrf: dict, phone: str, name: str = "张三") -> dict:
    resp = client.post(
        "/api/carrier/drivers",
        headers=csrf,
        json={"phone": phone, "password": TEMP_PASSWORD, "name": name},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _onboard_driver(app_client: TestClient, phone: str) -> TestClient:
    """用司机真实会话完成改密与身份绑定，返回已登录的司机端客户端。"""
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


def _create_vehicle(
    client: TestClient,
    csrf: dict,
    plate_no: str,
    *,
    vehicle_type: str = "平板货车",
    max_load_kg: int = 30000,
    length_m: float = 13.0,
) -> dict:
    resp = client.post(
        "/api/carrier/vehicles",
        headers=csrf,
        json={
            "plate_no": plate_no,
            "vehicle_type": vehicle_type,
            "length_m": length_m,
            "max_load_kg": max_load_kg,
            "owner_type": "公司",
            "document_status": "有效",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _dispatch(
    client: TestClient,
    csrf: dict,
    order_id: int,
    driver_account_id: int,
    vehicle_id: int,
    *,
    load: str = "2026-11-23T10:00:00+00:00",
    deliver: str = "2026-11-23T12:00:00+00:00",
    notes: str = "注意防潮",
):
    return client.post(
        "/api/carrier/tasks",
        headers=csrf,
        json={
            "order_id": order_id,
            "driver_account_id": driver_account_id,
            "vehicle_id": vehicle_id,
            "planned_load_at": load,
            "planned_deliver_at": deliver,
            "notes": notes,
        },
    )


class Fixture:
    """一套完整的物流公司 + 货主 + 已承接订单夹具。"""

    def __init__(self, client: TestClient, carrier_phone: str = "carrier1"):
        self.app = client
        self.carrier_id = _seed_account(client, carrier_phone, "物流公司")
        _seed_account(client, "shipper1", "货主")
        self.shipper = client
        self.shipper_headers = _login_headers(client, "shipper1", SHIPPER_PASSWORD)
        self.carrier = _client(client)
        self.carrier_headers = _login_headers(self.carrier, carrier_phone)
        self.order = self._accepted_order()

    def _accepted_order(self, **overrides) -> dict:
        published = _publish(self.shipper, self.shipper_headers, **overrides)
        assert published.status_code == 201, published.text
        order = published.json()
        accepted = self.carrier.post(
            f"/api/carrier/order-pool/{order['id']}/accept", headers=self.carrier_headers
        )
        assert accepted.status_code == 200, accepted.text
        return accepted.json()

    def driver(self, phone: str, name: str = "张三") -> tuple[dict, TestClient]:
        info = _create_driver(self.carrier, self.carrier_headers, phone, name)
        drv = _onboard_driver(self.app, phone)
        return info, drv

    def vehicle(self, plate: str, **kwargs) -> dict:
        return _create_vehicle(self.carrier, self.carrier_headers, plate, **kwargs)


# 1. 派单创建运输任务：占用资源、落派单历史、通知司机、任务号格式
def test_dispatch_creates_task_occupies_resources_and_notifies(client):
    f = Fixture(client)
    driver, _ = f.driver("driver-a")
    vehicle = f.vehicle("京A00001")

    resp = _dispatch(f.carrier, f.carrier_headers, f.order["id"], driver["account_id"], vehicle["id"])
    assert resp.status_code == 201, resp.text
    task = resp.json()
    assert re.match(r"^TASK-\d{6}-\d{4}$", task["task_no"])
    assert task["status"] == "待司机确认"
    assert task["order_id"] == f.order["id"]
    assert task["carrier_id"] == f.carrier_id
    assert task["driver_account_id"] == driver["account_id"]
    assert task["vehicle_id"] == vehicle["id"]
    assert task["planned_load_at"].startswith("2026-11-23T10:00")
    assert task["notes"] == "注意防潮"

    # 司机 / 车辆被任务占用
    d = f.carrier.get(f"/api/carrier/drivers/{driver['account_id']}").json()
    assert d["availability"] == "任务占用中"
    assert d["can_dispatch_new"] is False
    v = f.carrier.get(f"/api/carrier/vehicles/{vehicle['id']}").json()
    assert v["availability"] == "占用中"
    assert v["assignable"] is False

    # 派单历史留痕：原始为空、新司机 / 新车辆、原因、时间、角色
    history = f.carrier.get(f"/api/carrier/tasks/{task['id']}/dispatch-history").json()
    assert len(history) == 1
    assert history[0]["action"] == "派单"
    assert history[0]["new_driver_account_id"] == driver["account_id"]
    assert history[0]["new_vehicle_id"] == vehicle["id"]
    assert re.match(r"^DISP-\d{6}-\d{4}$", history[0]["dispatch_no"])
    assert history[0]["actor"] == "物流公司"
    assert history[0]["created_at"]

    # 司机收到待确认通知
    drv_client = _client(client)
    _login(drv_client, "driver-a", NEW_PASSWORD)
    notes = drv_client.get("/api/driver/notifications").json()
    assert any(n["kind"] == "新任务待确认" and n["related_id"] == task["id"] for n in notes)


# 2. 派单要求订单归属当前公司且已承接；他公司 / 待承接订单不可派
def test_dispatch_requires_owned_accepted_order(client):
    f = Fixture(client)
    driver, _ = f.driver("driver-b1")
    vehicle = f.vehicle("京B00001")

    # 待承接订单不可派
    pending = _publish(f.shipper, f.shipper_headers, cargo_name="待承接货").json()
    assert _dispatch(f.carrier, f.carrier_headers, pending["id"], driver["account_id"], vehicle["id"]).status_code == 409

    # 他公司承接的订单，本公司不可见也不可派
    other = Fixture(client, "carrier-other")
    od, _ = other.driver("driver-other")
    ov = other.vehicle("京B00002")
    assert other.carrier.get(f"/api/carrier/orders/{f.order['id']}").status_code == 404
    assert _dispatch(other.carrier, other.carrier_headers, f.order["id"], od["account_id"], ov["id"]).status_code == 404


# 3. 司机 / 车辆必须归属当前公司，跨公司主体一律 404
def test_dispatch_rejects_foreign_driver_and_vehicle(client):
    f = Fixture(client)
    driver, _ = f.driver("driver-c1")
    vehicle = f.vehicle("京C00001")

    other = Fixture(client, "carrier-foreign")
    foreign_driver, _ = other.driver("driver-foreign")
    foreign_vehicle = other.vehicle("京C00002")

    # 本公司的已承接订单 —— 用他公司司机派单
    r1 = _dispatch(f.carrier, f.carrier_headers, f.order["id"], foreign_driver["account_id"], vehicle["id"])
    assert r1.status_code == 404
    assert r1.json()["error"]["code"] == "司机不存在"
    # 用他公司车辆派单
    r2 = _dispatch(f.carrier, f.carrier_headers, f.order["id"], driver["account_id"], foreign_vehicle["id"])
    assert r2.status_code == 404
    assert r2.json()["error"]["code"] == "车辆不存在"


# 4. 不可用 / 未绑定的司机不可派单（可用性、雇佣关系、驾驶资格）
def test_dispatch_rejects_unavailable_or_unqualified_driver(client):
    f = Fixture(client)
    vehicle = f.vehicle("京D00001")

    # 未做身份绑定、无驾驶资格的司机
    raw = _create_driver(f.carrier, f.carrier_headers, "driver-raw")
    r = _dispatch(f.carrier, f.carrier_headers, f.order["id"], raw["account_id"], vehicle["id"])
    assert r.status_code == 409
    assert "资格" in r.json()["error"]["message"]

    driver, _ = f.driver("driver-paused")
    # 暂停接单
    f.carrier.post(
        f"/api/carrier/drivers/{driver['account_id']}/availability",
        headers=f.carrier_headers,
        json={"availability": "暂停接单"},
    )
    r = _dispatch(f.carrier, f.carrier_headers, f.order["id"], driver["account_id"], vehicle["id"])
    assert r.status_code == 409
    assert "不可派发新任务" in r.json()["error"]["message"]


# 5. 不可用车辆 / 不满足运输要求的车辆不可派单
def test_dispatch_rejects_unusable_or_mismatched_vehicle(client):
    f = Fixture(client)
    driver, _ = f.driver("driver-v")
    vehicle = f.vehicle("京E00001", vehicle_type="厢式货车", max_load_kg=2000, length_m=4.2)

    # 载重不满足 order 的 load_requirement（50 吨以上）
    r = _dispatch(f.carrier, f.carrier_headers, f.order["id"], driver["account_id"], vehicle["id"])
    assert r.status_code == 409
    assert "运输要求" in r.json()["error"]["message"]

    # 维修中的车辆不可派
    f.carrier.post(
        f"/api/carrier/vehicles/{vehicle['id']}/lifecycle",
        headers=f.carrier_headers,
        json={"lifecycle": "维修中"},
    )
    r = _dispatch(f.carrier, f.carrier_headers, f.order["id"], driver["account_id"], vehicle["id"])
    assert r.status_code == 409
    assert "维修" in r.json()["error"]["message"]

    # 冷链订单需要冷藏车
    cold = f._accepted_order(cold_chain=True, vehicle_type="冷藏车")
    cold_ok = f.vehicle("京E00002", vehicle_type="冷藏车", max_load_kg=30000, length_m=13.0)
    assert _dispatch(f.carrier, f.carrier_headers, cold["id"], driver["account_id"], cold_ok["id"]).status_code == 201
    normal = f.vehicle("京E00003", vehicle_type="平板货车", max_load_kg=30000, length_m=13.0)
    cold2 = f._accepted_order(cold_chain=True, vehicle_type="冷藏车")
    driver2, _ = f.driver("driver-v2")
    r = _dispatch(f.carrier, f.carrier_headers, cold2["id"], driver2["account_id"], normal["id"])
    assert r.status_code == 409
    assert "冷藏" in r.json()["error"]["message"]


# 6. 时间冲突：同一司机或车辆在有效任务的计划区间重叠即拒绝；不重叠可派
def test_dispatch_detects_time_conflict_on_driver_and_vehicle(client):
    f = Fixture(client)
    d1, _ = f.driver("driver-t1")
    d2, _ = f.driver("driver-t2")
    v1 = f.vehicle("京F00001")
    v2 = f.vehicle("京F00002")

    order2 = f._accepted_order(cargo_name="第二单")
    order3 = f._accepted_order(cargo_name="第三单")

    first = _dispatch(f.carrier, f.carrier_headers, f.order["id"], d1["account_id"], v1["id"],
                      load="2026-11-23T10:00:00+00:00", deliver="2026-11-23T12:00:00+00:00")
    assert first.status_code == 201, first.text

    # 同司机、不同车辆、区间重叠 → 冲突
    overlap_driver = _dispatch(f.carrier, f.carrier_headers, order2["id"], d1["account_id"], v2["id"],
                               load="2026-11-23T11:00:00+00:00", deliver="2026-11-23T13:00:00+00:00")
    assert overlap_driver.status_code == 409
    assert "时间冲突" in overlap_driver.json()["error"]["message"]

    # 同车辆、不同司机、区间重叠 → 冲突
    overlap_vehicle = _dispatch(f.carrier, f.carrier_headers, order2["id"], d2["account_id"], v1["id"],
                                load="2026-11-23T11:00:00+00:00", deliver="2026-11-23T13:00:00+00:00")
    assert overlap_vehicle.status_code == 409
    assert "时间冲突" in overlap_vehicle.json()["error"]["message"]

    # 不重叠（首单 12:00 结束，新单 12:00 开始）→ 允许
    free = _dispatch(f.carrier, f.carrier_headers, order3["id"], d2["account_id"], v2["id"],
                     load="2026-11-23T12:00:00+00:00", deliver="2026-11-23T14:00:00+00:00")
    assert free.status_code == 201, free.text


# 7. 司机确认任务：状态推进到待装货，记录确认时间并通知物流公司与货主
def test_driver_accepts_task(client):
    f = Fixture(client)
    driver, drv = f.driver("driver-accept")
    vehicle = f.vehicle("京G00001")
    task = _dispatch(f.carrier, f.carrier_headers, f.order["id"], driver["account_id"], vehicle["id"]).json()

    accepted = drv.post(
        f"/api/driver/tasks/{task['id']}/accept", headers=_driver_headers(drv, "driver-accept")
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "待装货"
    assert accepted.json()["accepted_at"]

    carrier_view = f.carrier.get(f"/api/carrier/tasks/{task['id']}").json()
    assert carrier_view["status"] == "待装货"
    assert carrier_view["accepted_at"] == accepted.json()["accepted_at"]

    # 物流公司与货主都收到司机已确认通知
    cnotes = f.carrier.get("/api/carrier/notifications").json()
    assert any(n["kind"] == "司机已确认任务" and n["related_id"] == task["id"] for n in cnotes)
    snotes = f.shipper.get("/api/shipper/notifications").json()
    assert any(n["kind"] == "司机已确认任务" and n["related_id"] == task["id"] for n in snotes)


# 8. 司机拒绝须填原因；任务终态已拒绝、订单回到待派单、资源释放、留痕并通知公司
def test_driver_rejects_task_with_reason(client):
    f = Fixture(client)
    driver, drv = f.driver("driver-reject")
    vehicle = f.vehicle("京H00001")
    task = _dispatch(f.carrier, f.carrier_headers, f.order["id"], driver["account_id"], vehicle["id"]).json()

    headers = _driver_headers(drv, "driver-reject")
    # 缺原因 → 422
    assert drv.post(f"/api/driver/tasks/{task['id']}/reject", json={}, headers=headers).status_code == 422

    rejected = drv.post(
        f"/api/driver/tasks/{task['id']}/reject",
        json={"reason": "车辆故障无法出发"},
        headers=headers,
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "已拒绝"
    assert rejected.json()["reject_reason"] == "车辆故障无法出发"

    # 订单回到待派单语义：已承接、可再次派单
    order_view = f.shipper.get(f"/api/shipper/orders/{f.order['id']}").json()
    assert order_view["status"] == "已承接"

    # 司机与车辆释放
    d = f.carrier.get(f"/api/carrier/drivers/{driver['account_id']}").json()
    assert d["availability"] == "可派单"
    v = f.carrier.get(f"/api/carrier/vehicles/{vehicle['id']}").json()
    assert v["availability"] == "可用"

    # 历史：派单 + 拒绝两条，拒绝原因入历史
    history = f.carrier.get(f"/api/carrier/tasks/{task['id']}/dispatch-history").json()
    assert len(history) == 2
    reject_row = [h for h in history if h["action"] == "司机拒绝"][0]
    assert reject_row["reason"] == "车辆故障无法出发"
    assert reject_row["actor"] == "司机"

    cnotes = f.carrier.get("/api/carrier/notifications").json()
    assert any(n["kind"] == "司机拒绝任务" for n in cnotes)

    # 已拒绝为终态，不能再确认
    assert drv.post(f"/api/driver/tasks/{task['id']}/accept", headers=headers).status_code == 409


# 9. 未起运重新派单：同一任务换司机 / 车辆，记录原新、原因与时间，留痕只读追加
def test_redispatch_before_departure_records_original_and_new(client):
    f = Fixture(client)
    d1, _ = f.driver("driver-rd1")
    d2, drv2 = f.driver("driver-rd2", "李四")
    v1 = f.vehicle("京I00001")
    v2 = f.vehicle("京I00002")

    task = _dispatch(f.carrier, f.carrier_headers, f.order["id"], d1["account_id"], v1["id"]).json()
    before = f.carrier.get(f"/api/carrier/tasks/{task['id']}/dispatch-history").json()

    red = f.carrier.post(
        f"/api/carrier/tasks/{task['id']}/redispatch",
        headers=f.carrier_headers,
        json={"driver_account_id": d2["account_id"], "vehicle_id": v2["id"], "reason": "原司机临时请假"},
    )
    assert red.status_code == 200, red.text
    assert red.json()["id"] == task["id"]  # 同一任务，换执行人
    assert red.json()["driver_account_id"] == d2["account_id"]
    assert red.json()["vehicle_id"] == v2["id"]
    assert red.json()["status"] == "待司机确认"

    # 原司机 / 车辆释放，新司机 / 车辆占用
    assert f.carrier.get(f"/api/carrier/drivers/{d1['account_id']}").json()["availability"] == "可派单"
    assert f.carrier.get(f"/api/carrier/vehicles/{v1['id']}").json()["availability"] == "可用"
    assert f.carrier.get(f"/api/carrier/drivers/{d2['account_id']}").json()["availability"] == "任务占用中"
    assert f.carrier.get(f"/api/carrier/vehicles/{v2['id']}").json()["availability"] == "占用中"

    # 历史追加一条，原记录不变，原 / 新司机车辆与原因齐备
    after = f.carrier.get(f"/api/carrier/tasks/{task['id']}/dispatch-history").json()
    assert len(after) == len(before) + 1
    assert before[0] == after[0]
    row = after[-1]
    assert row["action"] == "重新派单"
    assert row["original_driver_account_id"] == d1["account_id"]
    assert row["new_driver_account_id"] == d2["account_id"]
    assert row["original_vehicle_id"] == v1["id"]
    assert row["new_vehicle_id"] == v2["id"]
    assert row["reason"] == "原司机临时请假"
    assert row["created_at"]

    notes = _client(client)
    _login(notes, "driver-rd2", NEW_PASSWORD)
    assert any(n["kind"] == "新任务待确认" for n in notes.get("/api/driver/notifications").json())


# 10. 已起运的变更不得在此完成，必须走运输异常
def test_redispatch_after_departure_blocked(client):
    f = Fixture(client)
    d1, _ = f.driver("driver-dep1")
    d2, _ = f.driver("driver-dep2")
    v1 = f.vehicle("京J00001")
    v2 = f.vehicle("京J00002")
    task = _dispatch(f.carrier, f.carrier_headers, f.order["id"], d1["account_id"], v1["id"]).json()

    conn = _db(client)
    conn.execute("UPDATE transport_tasks SET status = '运输中' WHERE id = ?", (task["id"],))
    conn.commit()
    conn.close()

    resp = f.carrier.post(
        f"/api/carrier/tasks/{task['id']}/redispatch",
        headers=f.carrier_headers,
        json={"driver_account_id": d2["account_id"], "vehicle_id": v2["id"], "reason": "途中换人"},
    )
    assert resp.status_code == 409
    assert "运输异常" in resp.json()["error"]["message"]


# 11. 司机 H5 任务视图不含运费报价；司机只能看到派给自己的任务
def test_driver_task_view_has_no_quote_and_is_isolated(client):
    f = Fixture(client)
    d1, drv1 = f.driver("driver-view1")
    d2, drv2 = f.driver("driver-view2")
    v1 = f.vehicle("京K00001")
    v2 = f.vehicle("京K00002")
    task1 = _dispatch(f.carrier, f.carrier_headers, f.order["id"], d1["account_id"], v1["id"]).json()
    order2 = f._accepted_order(cargo_name="第二单")
    task2 = _dispatch(f.carrier, f.carrier_headers, order2["id"], d2["account_id"], v2["id"]).json()

    detail = drv1.get(f"/api/driver/tasks/{task1['id']}").json()
    forbidden = {"quote_amount_yuan", "quote_method", "quote_remarks", "accept_bargain",
                 "quote_amount_cents", "freight_quote"}
    assert forbidden.isdisjoint(detail.keys())
    assert detail["order_no"] == f.order["order_no"]
    assert detail["cargo_name"] == "冷轧钢板"
    assert detail["shipping"]["name"] == "上海发货点"
    assert detail["receiving"]["name"] == "苏州收货方"
    assert detail["vehicle_plate"] == "京K00001"
    assert detail["notes"] == "注意防潮"

    mine = [t["task_id"] for t in drv1.get("/api/driver/tasks").json()]
    assert mine == [task1["id"]]
    assert drv1.get(f"/api/driver/tasks/{task2['id']}").status_code == 404

    # 物流公司视角订单详情仍保留报价
    order_view = f.carrier.get(f"/api/carrier/orders/{f.order['id']}").json()
    assert order_view["quote_amount_yuan"] == "1200.50"


# 12. 司机业务端点走 BoundDriverDep：未绑定 / 其他角色被拦截
def test_driver_endpoints_require_bound_driver(client):
    f = Fixture(client)
    raw_phone = "driver-unbound"
    _create_driver(f.carrier, f.carrier_headers, raw_phone)
    drv = _client(client)
    _login(drv, raw_phone, TEMP_PASSWORD)
    assert drv.get("/api/driver/tasks").status_code == 403

    # 货主 / 未登录访问司机任务端点
    assert f.shipper.get("/api/driver/tasks").status_code == 404
    assert _client(client).get("/api/driver/tasks").status_code == 401


# 13. 写操作必须带 CSRF；跨角色访问派单端点返回 404
def test_dispatch_writes_require_csrf_and_role(client):
    f = Fixture(client)
    driver, _ = f.driver("driver-gate")
    vehicle = f.vehicle("京L00001")

    body = {
        "order_id": f.order["id"],
        "driver_account_id": driver["account_id"],
        "vehicle_id": vehicle["id"],
        "planned_load_at": "2026-11-23T10:00:00+00:00",
        "planned_deliver_at": "2026-11-23T12:00:00+00:00",
    }
    assert f.carrier.post("/api/carrier/tasks", json=body).status_code == 403
    shipper_resp = f.shipper.post("/api/carrier/tasks", json=body, headers=f.shipper_headers)
    assert shipper_resp.status_code == 404
    assert shipper_resp.json()["error"]["code"] == "资源不存在"


# 14. 同一订单不可重复派单（存在有效任务时）
def test_no_duplicate_active_task_per_order(client):
    f = Fixture(client)
    d1, _ = f.driver("driver-dup1")
    d2, _ = f.driver("driver-dup2")
    v1 = f.vehicle("京M00001")
    v2 = f.vehicle("京M00002")
    assert _dispatch(f.carrier, f.carrier_headers, f.order["id"], d1["account_id"], v1["id"]).status_code == 201
    dup = _dispatch(f.carrier, f.carrier_headers, f.order["id"], d2["account_id"], v2["id"],
                    load="2026-11-23T14:00:00+00:00", deliver="2026-11-23T16:00:00+00:00")
    assert dup.status_code == 409
    assert "已有运输任务" in dup.json()["error"]["message"]
