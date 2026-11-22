"""订单池与承接 seam 测试：浏览 / 筛选 / 详情 / 先到先得承接 / 归属 / 通知 / 门禁。

仅经 HTTP 黑盒断言：排列可用直接 sqlite3，所有业务结论只从接口读取获得。
"""

import re
import sqlite3

from fastapi.testclient import TestClient

PW = "pw123456"


def _db(client: TestClient) -> sqlite3.Connection:
    """打开测试库连接，仅用于布置夹具。"""
    return sqlite3.connect(client.app.state.settings.db_path)


def _approve(client: TestClient, phone: str) -> None:
    """布置夹具：把账号认证状态直接置为审核通过。"""
    conn = _db(client)
    conn.execute(
        "UPDATE accounts SET auth_status='审核通过' WHERE phone=?", (phone,)
    )
    conn.commit()
    conn.close()


def _disable(client: TestClient, phone: str) -> None:
    """布置夹具：把账号状态置为已禁用。"""
    conn = _db(client)
    conn.execute(
        "UPDATE accounts SET account_status='已禁用' WHERE phone=?", (phone,)
    )
    conn.commit()
    conn.close()


def _set_created_at(client: TestClient, order_id: int, value: str) -> None:
    """布置夹具：固定订单发布时间，供发布时间筛选确定性断言。"""
    conn = _db(client)
    conn.execute("UPDATE orders SET created_at=? WHERE id=?", (value, order_id))
    conn.commit()
    conn.close()


def _login(client: TestClient, phone: str):
    """经登录接口取得会话与 CSRF。"""
    return client.post("/api/auth/login", json={"phone": phone, "password": PW})


def _csrf(resp) -> dict:
    """从登录 / 注册响应取写操作所需的 CSRF 头。"""
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _account_id(client: TestClient, phone: str) -> int:
    """布置夹具：读取账号 id，用于断言承接归属。"""
    conn = _db(client)
    row = conn.execute("SELECT id FROM accounts WHERE phone=?", (phone,)).fetchone()
    conn.close()
    return row[0]


def _register_shipper(client: TestClient, phone: str, approved: bool = True) -> dict:
    """注册货主并登录；默认布置为审核通过，返回写操作 CSRF。"""
    reg = client.post(
        "/api/shipper/register", json={"phone": phone, "password": PW}
    )
    assert reg.status_code == 201, reg.text
    if approved:
        _approve(client, phone)
    return _csrf(_login(client, phone))


def _register_carrier(
    client: TestClient, phone: str, approved: bool = True
) -> dict:
    """注册物流公司并登录；默认布置为审核通过，返回写操作 CSRF。"""
    reg = client.post(
        "/api/carrier/register",
        json={"phone": phone, "password": PW, "company_name": f"{phone}物流公司"},
    )
    assert reg.status_code == 201, reg.text
    if approved:
        _approve(client, phone)
    return _csrf(_login(client, phone))


def _publish_body(**overrides) -> dict:
    """一份完整、合法的发布请求体。"""
    body = {
        "cargo_name": "冷轧钢板",
        "cargo_type": "钢材",
        "quantity": "50 吨",
        "weight": "50000 kg",
        "volume": "12.5 m³",
        "packaging": "钢带捆扎",
        "cargo_photos": ["cargo/steel-1.jpg"],
        "cargo_remarks": "需防潮",
        "shipping_source": "临时地址",
        "shipping_name": "上海临时发货点",
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
        "vehicle_type": "平板车",
        "vehicle_length": "13 米",
        "load_requirement": "30 吨以上",
        "cold_chain": False,
        "rain_protection": True,
        "enclosed_body": False,
        "special_loading": True,
        "other_services": "需叉车卸货",
        "transport_remarks": "工作日送达",
        "quote_method": "固定",
        "quote_amount_yuan": "1200.50",
        "accept_bargain": True,
        "quote_remarks": "含装卸",
    }
    body.update(overrides)
    return body


def _publish(client: TestClient, csrf: dict, **overrides):
    """经接口发布运输订单。"""
    return client.post(
        "/api/shipper/orders", json=_publish_body(**overrides), headers=csrf
    )


# --- slice 1: 浏览公共订单池与完整详情 ---


def test_approved_carrier_browses_pool_list_and_full_detail(client):
    """审核通过的物流公司可列出待承接货源，并读到货物 / 地点 / 联系人 / 要求 / 照片 / 报价 / 备注。"""
    scsrf = _register_shipper(client, "shipper1")
    order = _publish(client, scsrf).json()

    carrier = TestClient(client.app)
    _register_carrier(carrier, "carrierA")

    listed = carrier.get("/api/carrier/order-pool")
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [order["id"]]
    assert re.match(r"^ORD-\d{6}-\d{4}$", listed.json()[0]["order_no"])

    detail = carrier.get(f"/api/carrier/order-pool/{order['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["order_no"] == order["order_no"]
    assert body["cargo_name"] == "冷轧钢板"
    assert body["cargo_type"] == "钢材"
    assert body["quantity"] == "50 吨"
    assert body["weight"] == "50000 kg"
    assert body["cargo_photos"] == ["cargo/steel-1.jpg"]
    assert body["cargo_remarks"] == "需防潮"
    assert body["shipping_snapshot"]["name"] == "上海临时发货点"
    assert body["shipping_snapshot"]["contact"] == "王发货"
    assert body["shipping_snapshot"]["phone"] == "13800000001"
    assert body["receiving_snapshot"]["name"] == "苏州收货方"
    assert body["receiving_snapshot"]["contact"] == "李收货"
    assert body["vehicle_type"] == "平板车"
    assert body["vehicle_length"] == "13 米"
    assert body["rain_protection"] is True
    assert body["other_services"] == "需叉车卸货"
    assert body["transport_remarks"] == "工作日送达"
    # 运费报价对物流公司可见
    assert body["quote_method"] == "固定"
    assert body["quote_amount_yuan"] == "1200.50"
    assert body["accept_bargain"] is True


# --- slice 2: 订单池筛选（发货地 / 收货地 / 货物类型 / 车辆类型 / 重量 / 发布时间 / 运费范围） ---


def test_pool_filters_by_all_dimensions(client):
    """物流公司可按发货地、收货地、货物类型、车辆类型、重量、发布时间与运费范围筛选货源。"""
    scsrf = _register_shipper(client, "shipper1")
    a = _publish(
        client,
        scsrf,
        cargo_type="钢材",
        vehicle_type="平板车",
        weight="50000 kg",
        shipping_city="上海市",
        receiving_city="苏州市",
        quote_amount_yuan="1200.50",
    ).json()
    b = _publish(
        client,
        scsrf,
        cargo_type="水果",
        vehicle_type="冷藏车",
        weight="8000 kg",
        shipping_city="北京市",
        receiving_city="天津市",
        quote_amount_yuan="300.00",
    ).json()
    carrier = TestClient(client.app)
    _register_carrier(carrier, "carrierA")

    def ids(**params):
        resp = carrier.get("/api/carrier/order-pool", params=params)
        assert resp.status_code == 200
        return [row["id"] for row in resp.json()]

    assert ids(shipping_place="上海") == [a["id"]]
    assert ids(receiving_place="天津") == [b["id"]]
    assert ids(cargo_type="钢材") == [a["id"]]
    assert ids(vehicle_type="冷藏") == [b["id"]]
    assert ids(weight="8000") == [b["id"]]
    assert ids(quote_min_yuan="1000") == [a["id"]]
    assert ids(quote_max_yuan="500") == [b["id"]]
    assert ids(quote_min_yuan="500", quote_max_yuan="1500") == [a["id"]]

    # 发布时间用确定性夹具区分
    _set_created_at(client, a["id"], "2020-01-01T00:00:00+00:00")
    _set_created_at(client, b["id"], "2030-01-01T00:00:00+00:00")
    assert ids(published_from="2025-01-01T00:00:00+00:00") == [b["id"]]
    assert ids(published_to="2025-01-01T00:00:00+00:00") == [a["id"]]


def test_pool_lists_only_pending_orders(client):
    """订单池只展示待承接货源，已承接订单不再出现。"""
    scsrf = _register_shipper(client, "shipper1")
    a = _publish(client, scsrf).json()
    b = _publish(client, scsrf, cargo_name="水泥").json()
    carrier = TestClient(client.app)
    ccsrf = _register_carrier(carrier, "carrierA")

    assert {row["id"] for row in carrier.get("/api/carrier/order-pool").json()} == {
        a["id"],
        b["id"],
    }
    assert (
        carrier.post(
            f"/api/carrier/order-pool/{a['id']}/accept", headers=ccsrf
        ).status_code
        == 200
    )
    remaining = carrier.get("/api/carrier/order-pool").json()
    assert [row["id"] for row in remaining] == [b["id"]]


# --- slice 3: 承接后移出订单池、唯一归属、通知、快照不变 ---


def test_accept_moves_out_of_pool_assigns_owner_notifies_and_keeps_snapshots(client):
    """承接成功后订单移出公共池、唯一归属该公司，货主看到承接结果与通知，快照不被改写。"""
    scsrf = _register_shipper(client, "shipper1")
    order = _publish(client, scsrf).json()
    original_ship = dict(order["shipping_snapshot"])
    original_recv = dict(order["receiving_snapshot"])

    carrier = TestClient(client.app)
    ccsrf = _register_carrier(carrier, "carrierA")
    carrier_id = _account_id(client, "carrierA")

    accepted = carrier.post(
        f"/api/carrier/order-pool/{order['id']}/accept", headers=ccsrf
    )
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["status"] == "已承接"
    assert body["carrier_id"] == carrier_id
    assert body["accepted_at"]
    assert "T" in body["accepted_at"]
    # 承接按报价成立，不产生议价 / 竞价改写
    assert body["quote_amount_yuan"] == order["quote_amount_yuan"]
    assert body["cargo_name"] == order["cargo_name"]

    # 订单从公共池消失，再次读取详情不再可见
    assert carrier.get("/api/carrier/order-pool").json() == []
    assert (
        carrier.get(f"/api/carrier/order-pool/{order['id']}").status_code == 404
    )

    # 货主看到承接结果与所属物流公司
    shipper_view = client.get(f"/api/shipper/orders/{order['id']}").json()
    assert shipper_view["status"] == "已承接"
    assert shipper_view["carrier_id"] == carrier_id
    assert shipper_view["accepted_at"] == body["accepted_at"]

    # 收发快照承接后保持不变（承接只更新状态与归属字段）
    assert shipper_view["shipping_snapshot"] == original_ship
    assert shipper_view["receiving_snapshot"] == original_recv

    # 货主收到一条承接通知，关联该订单
    notes = client.get("/api/shipper/notifications").json()
    accepted_notes = [n for n in notes if n["kind"] == "订单已被承接"]
    assert len(accepted_notes) == 1
    assert accepted_notes[0]["related_id"] == order["id"]
    assert order["order_no"] in accepted_notes[0]["body"]


def test_second_carrier_cannot_accept_same_order(client):
    """先到先得：第一家公司承接后，第二家公司承接同一订单返回 409。"""
    scsrf = _register_shipper(client, "shipper1")
    order = _publish(client, scsrf).json()

    carrier_a = TestClient(client.app)
    acsrf = _register_carrier(carrier_a, "carrierA")
    assert (
        carrier_a.post(
            f"/api/carrier/order-pool/{order['id']}/accept", headers=acsrf
        ).status_code
        == 200
    )

    carrier_b = TestClient(client.app)
    bcsrf = _register_carrier(carrier_b, "carrierB")
    resp = carrier_b.post(
        f"/api/carrier/order-pool/{order['id']}/accept", headers=bcsrf
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "订单已被承接"

    # 归属仍为第一家公司，货主只看到一条承接通知
    view = client.get(f"/api/shipper/orders/{order['id']}").json()
    assert view["carrier_id"] == _account_id(client, "carrierA")
    notes = [n for n in client.get("/api/shipper/notifications").json()
             if n["kind"] == "订单已被承接"]
    assert len(notes) == 1


# --- slice 4: 门禁、CSRF、角色隔离 ---


def test_unapproved_and_disabled_and_unauthenticated_carrier_cannot_accept(client):
    """未认证、被禁用、未登录的物流公司都无法承接订单。"""
    scsrf = _register_shipper(client, "shipper1")
    order = _publish(client, scsrf).json()
    path = f"/api/carrier/order-pool/{order['id']}/accept"

    # 未登录
    anon = TestClient(client.app)
    anon_resp = anon.post(path, headers={"X-CSRF-Token": "x"})
    assert anon_resp.status_code == 401
    assert anon_resp.json()["error"]["code"] == "未登录"

    # 认证未通过
    pending = TestClient(client.app)
    pcsrf = _register_carrier(pending, "carrierPending", approved=False)
    resp = pending.post(path, headers=pcsrf)
    assert resp.status_code == 403
    assert "认证" in resp.json()["error"]["message"]

    # 已被禁用
    disabled = TestClient(client.app)
    dcsrf = _register_carrier(disabled, "carrierDisabled")
    _disable(client, "carrierDisabled")
    resp = disabled.post(path, headers=dcsrf)
    assert resp.status_code == 403

    # 订单仍待承接，未被任何人接走
    approver = TestClient(client.app)
    acsrf = _register_carrier(approver, "carrierA")
    assert approver.post(path, headers=acsrf).status_code == 200


def test_accept_requires_csrf_rejects_wrong_role_and_unknown_order(client):
    """承接是写操作：缺 CSRF 返回 403，非物流公司返回 404，未知订单返回 404。"""
    scsrf = _register_shipper(client, "shipper1")
    order = _publish(client, scsrf).json()
    carrier = TestClient(client.app)
    ccsrf = _register_carrier(carrier, "carrierA")
    path = f"/api/carrier/order-pool/{order['id']}/accept"

    assert carrier.post(path).status_code == 403
    assert carrier.post("/api/carrier/order-pool/999999/accept", headers=ccsrf).status_code == 404

    shipper_resp = client.post(path, headers=scsrf)
    assert shipper_resp.status_code == 404
    assert shipper_resp.json()["error"]["code"] == "资源不存在"

    assert client.post(f"/api/shipper/orders/{order['id']}/accept", headers=scsrf).status_code == 404
