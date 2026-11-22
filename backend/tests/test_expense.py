"""报销费用提交、审核、支付与重提 seam 测试：全部断言经 HTTP，数据准备可用 sqlite3。

覆盖司机按已完成运输任务提交多凭证费用、公司筛选与查看凭证、审核通过与驳回
（原因必填且司机可见）、审核与支付状态独立、线下付款标记已支付、驳回重提生成
新笔并保留原笔为历史、按收件人送达通知、跨主体 404 与管理无写入口。
"""

import sqlite3

from fastapi.testclient import TestClient

from app.core.security import hash_password

PASSWORD = "pw123456"
TEMP_PASSWORD = "temp123456"
NEW_PASSWORD = "new123456"


def _db(client: TestClient) -> sqlite3.Connection:
    return sqlite3.connect(client.app.state.settings.db_path)


def _seed_account(client: TestClient, phone: str, role: str) -> int:
    conn = _db(client)
    try:
        existing = conn.execute("SELECT id FROM accounts WHERE phone = ?", (phone,)).fetchone()
        if existing:
            return existing[0]
        from datetime import datetime, timezone

        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            """INSERT INTO accounts
               (phone, role, account_status, auth_status, password_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                phone,
                role,
                "正常使用",
                "审核通过",
                hash_password(PASSWORD),
                datetime.now(timezone.utc).isoformat(),
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


def _login(client: TestClient, phone: str, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"phone": phone, "password": password})


def _csrf(resp) -> dict:
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _login_headers(client: TestClient, phone: str, password: str = PASSWORD) -> dict:
    return _csrf(_login(client, phone, password))


def _client(client: TestClient) -> TestClient:
    return TestClient(client.app)


def _publish(client: TestClient, headers: dict):
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
    resp = client.post("/api/shipper/orders", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


class Fixture:
    """完整链路夹具：货主 + 物流公司 + 已完成运输任务。"""

    def __init__(self, client: TestClient, carrier_phone: str = "carrier1"):
        self.app = client
        self.carrier_id = _seed_account(client, carrier_phone, "物流公司")
        _seed_account(client, "shipper1", "货主")
        self.shipper = client
        self.shipper_headers = _login_headers(client, "shipper1")
        self.carrier = _client(client)
        self.carrier_headers = _login_headers(self.carrier, carrier_phone)
        order = _publish(self.shipper, self.shipper_headers)
        accepted = self.carrier.post(
            f"/api/carrier/order-pool/{order['id']}/accept", headers=self.carrier_headers
        )
        assert accepted.status_code == 200, accepted.text
        self.order = accepted.json()
        self.driver_phone = f"driver-{carrier_phone}"

    def completed_task(
        self, phone: str | None = None, *, complete: bool = True
    ) -> tuple[dict, TestClient, dict, int]:
        """建司机、派单、走完签收确认；complete=False 时停在待装货用于门禁测试。"""
        phone = phone or self.driver_phone
        created = self.carrier.post(
            "/api/carrier/drivers",
            headers=self.carrier_headers,
            json={"phone": phone, "password": TEMP_PASSWORD, "name": "张三"},
        )
        assert created.status_code == 201, created.text
        driver_id = created.json()["account_id"]

        drv = _client(self.app)
        login = _login(drv, phone, TEMP_PASSWORD)
        assert login.status_code == 200, login.text
        headers = _csrf(login)
        assert drv.post(
            "/api/driver/change-password", headers=headers, json={"new_password": NEW_PASSWORD}
        ).status_code == 204
        assert drv.post(
            "/api/driver/binding",
            headers=headers,
            json={
                "name": "张三",
                "id_number": "110101199001011234",
                "license_no": "LIC-2026-001",
                "license_type": "B2",
                "license_expiry": "2030-01-01",
            },
        ).status_code == 200
        headers = _csrf(_login(drv, phone, NEW_PASSWORD))

        vehicle = self.carrier.post(
            "/api/carrier/vehicles",
            headers=self.carrier_headers,
            json={
                "plate_no": f"京A{abs(hash(phone)) % 100000:05d}",
                "vehicle_type": "平板货车",
                "length_m": 13.0,
                "max_load_kg": 30000,
                "owner_type": "公司",
                "document_status": "有效",
            },
        )
        assert vehicle.status_code == 201, vehicle.text
        dispatched = self.carrier.post(
            "/api/carrier/tasks",
            headers=self.carrier_headers,
            json={
                "order_id": self.order["id"],
                "driver_account_id": driver_id,
                "vehicle_id": vehicle.json()["id"],
                "planned_load_at": "2026-11-23T10:00:00+00:00",
                "planned_deliver_at": "2026-11-23T12:00:00+00:00",
                "notes": "注意防潮",
            },
        )
        assert dispatched.status_code == 201, dispatched.text
        task = dispatched.json()
        task_id = task["id"]
        assert drv.post(f"/api/driver/tasks/{task_id}/accept", headers=headers).status_code == 200
        if not complete:
            return task, drv, headers, driver_id

        assert drv.post(
            f"/api/driver/tasks/{task_id}/checkin",
            headers=headers,
            json={
                "latitude": 31.2,
                "longitude": 121.5,
                "arrived_at": "2026-11-23T09:55:00+00:00",
                "photos": ["vouchers/checkin/site.jpg"],
                "notes": "已到发货点",
            },
        ).status_code == 201
        for phase in ("装货前", "装货中", "装货完成"):
            assert drv.post(
                f"/api/driver/tasks/{task_id}/loading/photos",
                headers=headers,
                json={"phase": phase, "paths": [f"vouchers/loading/{phase}.jpg"]},
            ).status_code == 201
        assert drv.post(
            f"/api/driver/tasks/{task_id}/start-transport",
            headers=headers,
            json={
                "cargo_confirmed": True,
                "vehicle_confirmed": True,
                "notes": "核对无误",
            },
        ).status_code == 200
        assert drv.post(
            f"/api/driver/tasks/{task_id}/arrival-checkin",
            headers=headers,
            json={
                "latitude": 31.28,
                "longitude": 120.62,
                "arrived_at": "2026-11-23T11:55:00+00:00",
                "photos": ["vouchers/arrival/site.jpg"],
                "notes": "已到收货点",
            },
        ).status_code == 201
        for phase in ("卸货前", "卸货中", "卸货完成"):
            assert drv.post(
                f"/api/driver/tasks/{task_id}/unloading/photos",
                headers=headers,
                json={"phase": phase, "paths": [f"vouchers/unloading/{phase}.jpg"]},
            ).status_code == 201
        assert drv.post(
            f"/api/driver/tasks/{task_id}/signoff",
            headers=headers,
            json={
                "receiving_condition": "完好",
                "received_at": "2026-11-23T12:20:00+00:00",
                "receiver_name": "李收货",
                "signature_photos": ["vouchers/signoff/signature.jpg"],
                "vouchers": ["vouchers/signoff/receipt.jpg"],
                "notes": "签收无误",
            },
        ).status_code == 200
        confirmed = self.carrier.post(
            f"/api/carrier/tasks/{task_id}/signoff/confirm",
            headers=self.carrier_headers,
            json={"confirmed": True, "notes": "确认完成"},
        )
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["task_status"] == "已完成"
        return task, drv, headers, driver_id


def _expense(**overrides):
    body = {
        "expense_type": "油费",
        "amount_yuan": "288.50",
        "incurred_at": "2026-11-23T11:00:00+00:00",
        "description": "高速服务区加油",
        "vouchers": ["vouchers/expense/fuel-1.jpg", "vouchers/expense/fuel-2.jpg"],
    }
    body.update(overrides)
    return body


def _submit(drv, headers, task_id, **overrides):
    return drv.post(
        f"/api/driver/tasks/{task_id}/expenses", headers=headers, json=_expense(**overrides)
    )


# 1. 司机按已完成运输任务单笔提交费用：类型/金额/时间/说明/多张凭证落库，公司可见
def test_driver_submits_expense_with_multiple_vouchers(client):
    f = Fixture(client)
    task, drv, headers, _ = f.completed_task()
    resp = _submit(drv, headers, task["id"])
    assert resp.status_code == 201, resp.text
    expense = resp.json()
    assert expense["task_id"] == task["id"]
    assert expense["expense_type"] == "油费"
    assert expense["amount_yuan"] == "288.50"
    assert expense["incurred_at"] == "2026-11-23T11:00:00+00:00"
    assert expense["description"] == "高速服务区加油"
    assert expense["vouchers"] == ["vouchers/expense/fuel-1.jpg", "vouchers/expense/fuel-2.jpg"]
    assert expense["review_status"] == "待审核"
    assert expense["payment_status"] == "待支付"
    assert expense["expense_no"].startswith("FE-")
    assert expense["driver_account_id"] > 0

    carrier_list = f.carrier.get("/api/carrier/expenses", headers=f.carrier_headers).json()
    assert len(carrier_list) == 1
    assert carrier_list[0]["expense_no"] == expense["expense_no"]
    assert len(carrier_list[0]["vouchers"]) == 2


# 2. 公司可按司机/任务/费用类型/提交时间/审核状态筛选并查看凭证
def test_carrier_filters_expenses_and_views_vouchers(client):
    f = Fixture(client)
    task, drv, headers, driver_id = f.completed_task()
    first = _submit(drv, headers, task["id"], expense_type="过路费", amount_yuan="60.00")
    assert first.status_code == 201, first.text
    second = _submit(drv, headers, task["id"], expense_type="停车费", amount_yuan="15.50")
    assert second.status_code == 201, second.text

    by_type = f.carrier.get(
        "/api/carrier/expenses", headers=f.carrier_headers, params={"expense_type": "过路费"}
    ).json()
    assert [e["expense_no"] for e in by_type] == [first.json()["expense_no"]]
    by_task = f.carrier.get(
        "/api/carrier/expenses", headers=f.carrier_headers, params={"task_id": task["id"]}
    ).json()
    assert len(by_task) == 2
    by_driver = f.carrier.get(
        "/api/carrier/expenses",
        headers=f.carrier_headers,
        params={"driver_account_id": driver_id},
    ).json()
    assert len(by_driver) == 2
    by_status = f.carrier.get(
        "/api/carrier/expenses",
        headers=f.carrier_headers,
        params={"review_status": "待审核"},
    ).json()
    assert len(by_status) == 2
    by_time = f.carrier.get(
        "/api/carrier/expenses",
        headers=f.carrier_headers,
        params={"submitted_from": "2030-01-01T00:00:00+00:00"},
    ).json()
    assert by_time == []
    detail = f.carrier.get(
        f"/api/carrier/expenses/{first.json()['id']}", headers=f.carrier_headers
    )
    assert detail.status_code == 200
    assert detail.json()["vouchers"] == first.json()["vouchers"]


# 3. 未完成任务不可提交费用；非本人任务提交 404
def test_expense_requires_completed_owned_task(client):
    f = Fixture(client)
    task, drv, headers, _ = f.completed_task()
    other_f = Fixture(client, "carrier-other")
    other_task, _, _, _ = other_f.completed_task()
    assert _submit(drv, headers, other_task["id"]).status_code == 404

    fresh = Fixture(client, "carrier-fresh")
    pending_task, pending_drv, pending_headers, _ = fresh.completed_task(complete=False)
    blocked = _submit(pending_drv, pending_headers, pending_task["id"])
    assert blocked.status_code == 409
    assert "已完成" in blocked.json()["error"]["message"]


# 4. 司机端费用出参不含运费报价
def test_driver_expense_output_has_no_quote(client):
    f = Fixture(client)
    task, drv, headers, _ = f.completed_task()
    created = _submit(drv, headers, task["id"])
    assert created.status_code == 201, created.text
    mine = drv.get("/api/driver/expenses", headers=headers).json()
    assert len(mine) == 1
    assert not any(key.startswith("quote") for key in mine[0])
    assert "quote_amount_yuan" not in mine[0]


def _review(carrier, headers, expense_id, decision, reason=""):
    return carrier.post(
        f"/api/carrier/expenses/{expense_id}/review",
        headers=headers,
        json={"decision": decision, "reason": reason},
    )


def _mark_paid(carrier, headers, expense_id):
    return carrier.post(f"/api/carrier/expenses/{expense_id}/mark-paid", headers=headers)


# 5. 审核驳回原因必填且司机可见；审核通过不改动支付状态
def test_review_reject_reason_visible_and_status_independent(client):
    f = Fixture(client)
    task, drv, headers, _ = f.completed_task()
    rejected = _submit(drv, headers, task["id"], expense_type="维修费", amount_yuan="1200.00")
    assert rejected.status_code == 201, rejected.text
    expense_id = rejected.json()["id"]

    invalid = _review(f.carrier, f.carrier_headers, expense_id, "审核驳回", "   ")
    assert invalid.status_code == 422
    assert "驳回原因" in invalid.text

    done = _review(f.carrier, f.carrier_headers, expense_id, "审核驳回", "发票缺失，请补充原件")
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["review_status"] == "审核驳回"
    assert body["review_reason"] == "发票缺失，请补充原件"
    assert body["payment_status"] == "待支付"
    assert body["reviewed_by_account_id"] == f.carrier_id
    assert body["reviewed_at"] is not None

    mine = drv.get("/api/driver/expenses", headers=headers).json()
    assert mine[0]["review_status"] == "审核驳回"
    assert mine[0]["review_reason"] == "发票缺失，请补充原件"

    approved = _submit(drv, headers, task["id"], expense_type="其他", amount_yuan="35.00")
    assert approved.status_code == 201, approved.text
    passed = _review(f.carrier, f.carrier_headers, approved.json()["id"], "审核通过")
    assert passed.status_code == 200, passed.text
    assert passed.json()["review_status"] == "审核通过"
    assert passed.json()["payment_status"] == "待支付"

    notes = drv.get("/api/driver/notifications", headers=headers).json()
    assert any(n["kind"] == "费用审核驳回" and "发票缺失" in n["body"] for n in notes)
    assert any(n["kind"] == "费用审核通过" for n in notes)


# 6. 线下付款后标记已支付：记录操作人与时间，审核状态保持独立
def test_mark_paid_records_actor_time_and_keeps_review_status(client):
    f = Fixture(client)
    task, drv, headers, _ = f.completed_task()
    expense_id = _submit(drv, headers, task["id"]).json()["id"]

    too_early = _mark_paid(f.carrier, f.carrier_headers, expense_id)
    assert too_early.status_code == 409
    assert _review(f.carrier, f.carrier_headers, expense_id, "审核通过").status_code == 200

    paid = _mark_paid(f.carrier, f.carrier_headers, expense_id)
    assert paid.status_code == 200, paid.text
    body = paid.json()
    assert body["payment_status"] == "已支付"
    assert body["review_status"] == "审核通过"
    assert body["paid_at"] is not None
    assert body["paid_by_account_id"] == f.carrier_id

    again = _mark_paid(f.carrier, f.carrier_headers, expense_id)
    assert again.status_code == 409

    paid_list = f.carrier.get(
        "/api/carrier/expenses", headers=f.carrier_headers, params={"payment_status": "已支付"}
    ).json()
    assert [e["id"] for e in paid_list] == [expense_id]
    notes = drv.get("/api/driver/notifications", headers=headers).json()
    assert any(n["kind"] == "费用已支付" for n in notes)


# 7. 提交通知公司、跨公司审核 404
def test_submit_notifies_carrier_and_cross_carrier_review_404(client):
    f = Fixture(client)
    task, drv, headers, _ = f.completed_task()
    expense_id = _submit(drv, headers, task["id"]).json()["id"]

    carrier_notes = f.carrier.get("/api/carrier/notifications", headers=f.carrier_headers).json()
    assert any(n["kind"] == "费用提交" and n["related_id"] == expense_id for n in carrier_notes)

    other = Fixture(client, "carrier-other2")
    assert _review(other.carrier, other.carrier_headers, expense_id, "审核通过").status_code == 404
    assert other.carrier.get(f"/api/carrier/expenses/{expense_id}", headers=other.carrier_headers).status_code == 404


def _resubmit(drv, headers, expense_id, **overrides):
    return drv.post(
        f"/api/driver/expenses/{expense_id}/resubmit", headers=headers, json=_expense(**overrides)
    )


# 8. 驳回后重提生成新笔并关联原笔，原笔保留为历史
def test_resubmit_creates_new_expense_and_keeps_original(client):
    f = Fixture(client)
    task, drv, headers, _ = f.completed_task()
    original = _submit(drv, headers, task["id"])
    assert original.status_code == 201, original.text
    old = original.json()
    assert _review(f.carrier, f.carrier_headers, old["id"], "审核驳回", "金额有误，请重填").status_code == 200

    resubmitted = _resubmit(
        drv, headers, old["id"], expense_type="过路费", amount_yuan="199.90",
        description="重新核对后的过路费", vouchers=["vouchers/expense/new-1.jpg"],
    )
    assert resubmitted.status_code == 201, resubmitted.text
    new = resubmitted.json()
    assert new["id"] != old["id"]
    assert new["expense_no"] != old["expense_no"]
    assert new["replaced_by"] == old["id"]
    assert new["review_status"] == "待审核"
    assert new["payment_status"] == "待支付"
    assert new["expense_type"] == "过路费"
    assert new["amount_yuan"] == "199.90"
    assert new["description"] == "重新核对后的过路费"
    assert new["vouchers"] == ["vouchers/expense/new-1.jpg"]

    mine = drv.get("/api/driver/expenses", headers=headers).json()
    by_id = {e["id"]: e for e in mine}
    assert by_id[old["id"]]["review_status"] == "审核驳回"
    assert by_id[old["id"]]["review_reason"] == "金额有误，请重填"
    assert by_id[old["id"]]["superseded_by"] == new["id"]
    assert by_id[new["id"]]["review_status"] == "待审核"

    carrier_rows = f.carrier.get(
        "/api/carrier/expenses", headers=f.carrier_headers, params={"task_id": task["id"]}
    ).json()
    assert {e["id"] for e in carrier_rows} == {old["id"], new["id"]}

    # 重复重提、对已通过费用重提均不可
    assert _resubmit(drv, headers, old["id"]).status_code == 409
    assert _review(f.carrier, f.carrier_headers, new["id"], "审核通过").status_code == 200
    assert _resubmit(drv, headers, new["id"]).status_code == 409
    assert _resubmit(drv, headers, 999999).status_code == 404

    carrier_notes = f.carrier.get("/api/carrier/notifications", headers=f.carrier_headers).json()
    assert any(n["kind"] == "费用提交" and n["related_id"] == new["id"] for n in carrier_notes)


# 9. 管理员对费用只读：无写入口，写路径一律 404
def test_admin_cannot_write_expenses(client):
    f = Fixture(client)
    task, drv, headers, _ = f.completed_task()
    expense_id = _submit(drv, headers, task["id"]).json()["id"]
    admin = _client(client)
    admin_headers = _csrf(_login(admin, "admin", "admin123456"))

    assert _review(admin, admin_headers, expense_id, "审核通过").status_code == 404
    assert _mark_paid(admin, admin_headers, expense_id).status_code == 404
    assert _submit(admin, admin_headers, task["id"]).status_code == 404
    assert admin.get("/api/carrier/expenses", headers=admin_headers).status_code == 404


# 10. 跨主体司机不可重提他人费用
def test_driver_cannot_resubmit_other_expense(client):
    f = Fixture(client)
    task, drv, headers, _ = f.completed_task()
    expense_id = _submit(drv, headers, task["id"]).json()["id"]
    assert _review(f.carrier, f.carrier_headers, expense_id, "审核驳回", "补凭证").status_code == 200

    other = Fixture(client, "carrier-other3")
    _, other_drv, other_headers, _ = other.completed_task()
    assert _resubmit(other_drv, other_headers, expense_id).status_code == 404
