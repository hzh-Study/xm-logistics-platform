"""运输订单发布 seam 测试：货物、快照、报价、门禁与隔离，仅经 HTTP 黑盒断言。"""

import re

from fastapi.testclient import TestClient

ADMIN = ("admin", "admin123456")
PW = "pw123456"


def _register(client: TestClient, phone: str):
    """注册货主并取得会话与 CSRF。"""
    return client.post(
        "/api/shipper/register", json={"phone": phone, "password": PW}
    )


def _login(client: TestClient, phone: str, password: str = PW):
    """登录并取得会话与 CSRF。"""
    return client.post("/api/auth/login", json={"phone": phone, "password": password})


def _csrf(resp) -> dict:
    """从登录 / 注册响应取写操作所需的 CSRF 头。"""
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _current_csrf(client: TestClient) -> dict:
    """从 /me 恢复当前会话的 CSRF 头。"""
    return {"X-CSRF-Token": client.get("/api/auth/me").json()["csrf_token"]}


def _approved_shipper(client: TestClient, phone: str) -> dict:
    """注册货主、提交认证并由管理员审核通过，返回货主写操作 CSRF。"""
    reg = _register(client, phone)
    assert reg.status_code == 201
    assert _submit_cert(client, _csrf(reg)).status_code == 201
    admin = _login(client, *ADMIN)
    admin_csrf = _csrf(admin)
    rows = client.get("/api/admin/shipper-certifications").json()
    cert_id = next(r["certification_id"] for r in rows if r["phone"] == phone)
    review = client.post(
        f"/api/admin/shipper-certifications/{cert_id}/review",
        json={"decision": "审核通过"},
        headers=admin_csrf,
    )
    assert review.status_code == 200
    assert _login(client, phone, PW).status_code == 200
    return _current_csrf(client)


def _submit_cert(client: TestClient, csrf: dict):
    """提交一份个人认证资料。"""
    return client.post(
        "/api/shipper/certification",
        json={
            "cert_type": "个人",
            "name": "张三",
            "id_number": "110101199001011234",
            "contact_phone": "13900000000",
            "documents": ["certs/id-front.png"],
        },
        headers=csrf,
    )


def _warehouse_body(**overrides) -> dict:
    """一份合法的仓库请求体。"""
    body = {
        "name": "华东一号仓",
        "contact": "王经理",
        "phone": "13800000001",
        "province": "上海市",
        "city": "上海市",
        "district": "浦东新区",
        "detail_address": "张江路 100 号 1 幢",
        "type": "普通仓库",
        "remarks": "常温库，靠码头",
    }
    body.update(overrides)
    return body


def _create_warehouse(client: TestClient, csrf: dict, **overrides):
    """经接口创建仓库。"""
    return client.post(
        "/api/shipper/warehouses", json=_warehouse_body(**overrides), headers=csrf
    )


_TEMP_SHIPPING = {
    "shipping_name": "临时发货点",
    "shipping_contact": "发货联系人",
    "shipping_phone": "13800000001",
    "shipping_province": "上海市",
    "shipping_city": "上海市",
    "shipping_district": "浦东新区",
    "shipping_detail_address": "张江路 100 号",
}


def _publish_body(**overrides) -> dict:
    """一份完整、合法的发布请求体（临时地址发货 + 固定报价）。"""
    body = {
        "cargo_name": "冷轧钢板",
        "cargo_type": "钢材",
        "quantity": "50 吨",
        "weight": "50000 kg",
        "volume": "12.5 m³",
        "packaging": "钢带捆扎",
        "cargo_photos": ["cargo/steel-1.jpg", "cargo/steel-2.jpg"],
        "cargo_remarks": "需防潮",
        "shipping_source": "临时地址",
        **_TEMP_SHIPPING,
        "receiving_name": "收货公司",
        "receiving_contact": "收货联系人",
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


def _warehouse_publish_body(warehouse_id: int, **overrides) -> dict:
    """从已有仓库发货的发布请求体。"""
    body = _publish_body()
    for key in _TEMP_SHIPPING:
        body.pop(key)
    body["shipping_source"] = "仓库"
    body["warehouse_id"] = warehouse_id
    body.update(overrides)
    return body


def _publish(client: TestClient, csrf: dict, **overrides):
    """经接口发布运输订单。"""
    return client.post("/api/shipper/orders", json=_publish_body(**overrides), headers=csrf)


# --- slice 1: 发布完整货物信息并读回 ---


def test_approved_shipper_publishes_full_order_and_reads_back(client):
    """审核通过的货主可发布含全部货物 / 要求 / 报价的订单，进入待承接。"""
    csrf = _approved_shipper(client, "shipper1")
    resp = _publish(client, csrf)
    assert resp.status_code == 201
    body = resp.json()

    assert re.match(r"^ORD-\d{6}-\d{4}$", body["order_no"])
    assert body["order_no"].endswith("-0001")
    assert body["status"] == "待承接"
    assert body["shipper_id"] == client.get("/api/auth/me").json()["id"]
    assert body["cargo_name"] == "冷轧钢板"
    assert body["cargo_type"] == "钢材"
    assert body["quantity"] == "50 吨"
    assert body["weight"] == "50000 kg"
    assert body["volume"] == "12.5 m³"
    assert body["packaging"] == "钢带捆扎"
    assert body["cargo_photos"] == ["cargo/steel-1.jpg", "cargo/steel-2.jpg"]
    assert body["cargo_remarks"] == "需防潮"

    assert body["vehicle_type"] == "平板车"
    assert body["vehicle_length"] == "13 米"
    assert body["load_requirement"] == "30 吨以上"
    assert body["rain_protection"] is True
    assert body["special_loading"] is True
    assert body["cold_chain"] is False
    assert body["enclosed_body"] is False
    assert body["other_services"] == "需叉车卸货"
    assert body["transport_remarks"] == "工作日送达"

    assert body["quote_method"] == "固定"
    assert body["quote_amount_yuan"] == "1200.50"
    assert body["accept_bargain"] is True

    detail = client.get(f"/api/shipper/orders/{body['id']}")
    assert detail.status_code == 200
    assert detail.json() == body
    assert client.get("/api/shipper/orders").json() == [body]


def test_publish_success_notification_recorded(client):
    """发布成功后货主收到一条发布成功通知，关联该订单。"""
    csrf = _approved_shipper(client, "shipper1")
    order = _publish(client, csrf).json()
    notes = client.get("/api/shipper/notifications").json()
    published = [n for n in notes if n["kind"] == "订单发布成功"]
    assert len(published) == 1
    assert published[0]["related_id"] == order["id"]
    assert order["order_no"] in published[0]["body"]


# --- slice 2: 发货 / 收货快照在发布时固化 ---


def test_publish_from_warehouse_freezes_shipping_snapshot(client):
    """选择仓库发货时，发货快照取自仓库当前资料并固化在订单上。"""
    csrf = _approved_shipper(client, "shipper1")
    warehouse = _create_warehouse(client, csrf).json()
    published = client.post(
        "/api/shipper/orders",
        json=_warehouse_publish_body(warehouse["id"]),
        headers=csrf,
    )
    assert published.status_code == 201
    body = published.json()
    snap = body["shipping_snapshot"]
    assert snap["source"] == "仓库"
    assert snap["warehouse_id"] == warehouse["id"]
    assert snap["name"] == warehouse["name"]
    assert snap["contact"] == warehouse["contact"]
    assert snap["phone"] == warehouse["phone"]
    assert snap["province"] == warehouse["province"]
    assert snap["city"] == warehouse["city"]
    assert snap["district"] == warehouse["district"]
    assert snap["detail_address"] == warehouse["detail_address"]
    assert snap["type"] == warehouse["type"]


def test_temporary_address_shipping_and_receiving_snapshots_are_frozen(client):
    """临时地址发货时，发货与收货快照按填写内容固化。"""
    csrf = _approved_shipper(client, "shipper1")
    body = _publish(client, csrf).json()
    ship = body["shipping_snapshot"]
    assert ship["source"] == "临时地址"
    assert ship["warehouse_id"] is None
    assert ship["name"] == "临时发货点"
    assert ship["contact"] == "发货联系人"
    assert ship["phone"] == "13800000001"
    assert ship["detail_address"] == "张江路 100 号"

    recv = body["receiving_snapshot"]
    assert recv["name"] == "收货公司"
    assert recv["contact"] == "收货联系人"
    assert recv["phone"] == "13900000002"
    assert recv["province"] == "江苏省"
    assert recv["city"] == "苏州市"
    assert recv["district"] == "工业园区"
    assert recv["detail_address"] == "星湖街 200 号"


def test_warehouse_changes_never_rewrite_frozen_snapshots(client):
    """仓库改名 / 改址 / 停用后，既有订单的发货与收货快照保持不变。"""
    csrf = _approved_shipper(client, "shipper1")
    warehouse = _create_warehouse(client, csrf).json()
    order = client.post(
        "/api/shipper/orders",
        json=_warehouse_publish_body(warehouse["id"]),
        headers=csrf,
    ).json()
    original_ship = dict(order["shipping_snapshot"])
    original_recv = dict(order["receiving_snapshot"])

    update = client.put(
        f"/api/shipper/warehouses/{warehouse['id']}",
        json=_warehouse_body(name="改名后的仓库", detail_address="新地址 999 号"),
        headers=csrf,
    )
    assert update.status_code == 200
    assert update.json()["name"] == "改名后的仓库"
    assert client.post(
        f"/api/shipper/warehouses/{warehouse['id']}/disable", headers=csrf
    ).json()["status"] == "停用"

    after = client.get(f"/api/shipper/orders/{order['id']}").json()
    assert after["shipping_snapshot"] == original_ship
    assert after["receiving_snapshot"] == original_recv
    listed = client.get("/api/shipper/orders").json()[0]
    assert listed["shipping_snapshot"] == original_ship
    assert listed["receiving_snapshot"] == original_recv


def test_snapshot_columns_reject_direct_rewrite(client):
    """快照在库层受保护：任何直接改写已发布订单快照的尝试都被拒绝。"""
    import sqlite3

    csrf = _approved_shipper(client, "shipper1")
    order = _publish(client, csrf).json()
    conn = sqlite3.connect(client.app.state.settings.db_path)
    try:
        conn.execute(
            "UPDATE orders SET ship_name = '篡改' WHERE id = ?", (order["id"],)
        )
        conn.commit()
        rewritten = True
    except sqlite3.IntegrityError:
        rewritten = False
    finally:
        conn.close()
    assert rewritten is False
    assert client.get(f"/api/shipper/orders/{order['id']}").json()[
        "shipping_snapshot"
    ] == order["shipping_snapshot"]


# --- slice 3: 报价方式与展示标记 ---


def test_quote_negotiable_and_other_methods(client):
    """可协商 / 其他报价方式无需金额，「接受议价」只是展示标记。"""
    csrf = _approved_shipper(client, "shipper1")
    negotiable = _publish(
        client,
        csrf,
        quote_method="可协商",
        quote_amount_yuan=None,
        accept_bargain=False,
    )
    assert negotiable.status_code == 201
    assert negotiable.json()["quote_method"] == "可协商"
    assert negotiable.json()["quote_amount_yuan"] == "0.00"
    assert negotiable.json()["accept_bargain"] is False

    other = _publish(
        client,
        csrf,
        quote_method="其他",
        quote_amount_yuan=None,
        quote_remarks="货到付款",
        cargo_name="水泥",
    )
    assert other.status_code == 201
    assert other.json()["quote_method"] == "其他"
    assert other.json()["quote_amount_yuan"] == "0.00"
    assert other.json()["quote_remarks"] == "货到付款"


def test_fixed_quote_requires_amount(client):
    """固定报价必须填写金额，否则在边界返回校验错误。"""
    csrf = _approved_shipper(client, "shipper1")
    resp = _publish(client, csrf, quote_amount_yuan=None)
    assert resp.status_code == 422
    assert "金额" in str(resp.json()["error"]["details"])
    assert client.get("/api/shipper/orders").json() == []


def test_quote_amount_converted_to_integer_cents_in_storage(client):
    """报价在边界以元表达，库内以分为单位精确存储。"""
    import sqlite3

    csrf = _approved_shipper(client, "shipper1")
    order = _publish(client, csrf, quote_amount_yuan="1200.05").json()
    conn = sqlite3.connect(client.app.state.settings.db_path)
    row = conn.execute(
        "SELECT quote_amount_cents FROM orders WHERE id = ?", (order["id"],)
    ).fetchone()
    conn.close()
    assert row[0] == 120005


# --- slice 4: 门禁、校验、隔离 ---


def test_publish_still_blocked_without_approved_certification(client):
    """认证未通过时完整请求也被 403 阻断并给出明确原因，且不落订单。"""
    reg = _register(client, "shipper1")
    resp = _publish(client, _csrf(reg))
    assert resp.status_code == 403
    message = resp.json()["error"]["message"]
    assert "审核通过" in message or "认证" in message
    assert client.get("/api/shipper/orders").json() == []
    assert client.get("/api/shipper/notifications").json() == []


def test_publish_requires_csrf_and_shipper_role(client):
    """发布是写操作：缺 CSRF 返回 403，非货主角色返回 404。"""
    csrf = _approved_shipper(client, "shipper1")
    assert (
        client.post("/api/shipper/orders", json=_publish_body()).status_code == 403
    )
    admin = _login(client, *ADMIN)
    resp = client.post(
        "/api/shipper/orders", json=_publish_body(), headers=_csrf(admin)
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "资源不存在"
    assert csrf  # 确保前面已取得货主会话


def test_publish_validates_photos_and_unknown_fields(client):
    """货物照片须为库内相对路径；未知字段被拒绝。"""
    csrf = _approved_shipper(client, "shipper1")
    bad_path = _publish(client, csrf, cargo_photos=["/etc/passwd"])
    assert bad_path.status_code == 422
    bad_field = _publish(client, csrf, **{"unknown_field": "x"})
    assert bad_field.status_code == 422
    assert client.get("/api/shipper/orders").json() == []


def test_shippers_isolated_on_order_detail(client):
    """货主只能读取自己的订单详情，越权读取返回 404。"""
    csrf1 = _approved_shipper(client, "shipper1")
    order = _publish(client, csrf1).json()

    _approved_shipper(client, "shipper2")
    resp = client.get(f"/api/shipper/orders/{order['id']}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "订单不存在"


# --- slice 5: 列表筛选 ---


def test_list_orders_filters_by_number_status_and_places(client):
    """货主可按订单号、状态、货物名称、发货地与收货地筛选订单。"""
    csrf = _approved_shipper(client, "shipper1")
    a = _publish(
        client,
        csrf,
        cargo_name="钢材",
        shipping_detail_address="张江路 100 号",
        receiving_city="苏州市",
    ).json()
    b = _publish(
        client,
        csrf,
        cargo_name="水泥",
        shipping_detail_address="世纪大道 1 号",
        receiving_city="无锡市",
        quote_method="可协商",
        quote_amount_yuan=None,
    ).json()

    def ids(**params):
        return [row["id"] for row in client.get("/api/shipper/orders", params=params).json()]

    assert ids(order_no=a["order_no"]) == [a["id"]]
    assert ids(status="待承接") == [b["id"], a["id"]]
    assert ids(cargo_name="钢材") == [a["id"]]
    assert ids(shipping_place="张江路") == [a["id"]]
    assert ids(receiving_place="苏州") == [a["id"]]
    assert ids(status="已完成") == []
