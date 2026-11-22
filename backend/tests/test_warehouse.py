"""仓库管理 seam 测试：列表、搜索、增删改状态与权限隔离，仅经 HTTP 黑盒断言。"""

from fastapi.testclient import TestClient

PW = "pw123456"


def _register(client: TestClient, phone: str):
    """注册货主并取得会话与 CSRF。"""
    return client.post(
        "/api/shipper/register", json={"phone": phone, "password": PW}
    )


def _csrf(resp) -> dict:
    """从注册 / 登录响应取写操作的 CSRF 头。"""
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


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


def _create(client: TestClient, csrf: dict, **overrides):
    """经接口创建仓库。"""
    return client.post(
        "/api/shipper/warehouses", json=_warehouse_body(**overrides), headers=csrf
    )


# --- slice 1: 列表与按名称搜索 ---


def test_new_shipper_has_empty_warehouse_list(client):
    """新货主的仓库列表为空。"""
    _register(client, "wh1")
    resp = client.get("/api/shipper/warehouses")
    assert resp.status_code == 200
    assert resp.json() == []


def test_shipper_creates_warehouse_and_reads_it_back(client):
    """货主创建仓库后，列表返回名称 / 位置 / 联系人 / 电话 / 类型 / 状态。"""
    reg = _register(client, "wh1")
    created = _create(client, _csrf(reg))
    assert created.status_code == 201
    body = created.json()
    assert body["id"] > 0
    assert body["shipper_id"] > 0
    assert body["name"] == "华东一号仓"
    assert body["contact"] == "王经理"
    assert body["phone"] == "13800000001"
    assert body["province"] == "上海市"
    assert body["city"] == "上海市"
    assert body["district"] == "浦东新区"
    assert body["detail_address"] == "张江路 100 号 1 幢"
    assert body["type"] == "普通仓库"
    assert body["remarks"] == "常温库，靠码头"
    assert body["status"] == "正常"
    assert "上海市" in body["location"]
    assert "浦东新区" in body["location"]

    rows = client.get("/api/shipper/warehouses").json()
    assert len(rows) == 1
    assert rows[0]["id"] == body["id"]
    assert rows[0]["name"] == body["name"]


def test_warehouse_search_by_name(client):
    """按名称搜索只返回匹配的仓库，支持模糊匹配。"""
    reg = _register(client, "wh1")
    csrf = _csrf(reg)
    assert _create(client, csrf, name="华东一号仓").status_code == 201
    assert _create(client, csrf, name="华南二号仓").status_code == 201

    rows = client.get("/api/shipper/warehouses", params={"name": "华东"}).json()
    assert [row["name"] for row in rows] == ["华东一号仓"]
    rows = client.get("/api/shipper/warehouses", params={"name": "不存在"}).json()
    assert rows == []


# --- slice 2: 修改、停用与状态筛选 ---


def test_shipper_updates_warehouse_master_data(client):
    """货主修改仓库主数据后按接口读回为新值，状态不被改写。"""
    reg = _register(client, "wh1")
    csrf = _csrf(reg)
    created = _create(client, csrf).json()

    resp = client.put(
        f"/api/shipper/warehouses/{created['id']}",
        json=_warehouse_body(
            name="华东二号仓",
            contact="李经理",
            phone="13900000002",
            detail_address="科苑路 200 号",
            remarks="改为恒温库",
        ),
        headers=csrf,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == created["id"]
    assert body["name"] == "华东二号仓"
    assert body["contact"] == "李经理"
    assert body["phone"] == "13900000002"
    assert body["detail_address"] == "科苑路 200 号"
    assert body["remarks"] == "改为恒温库"
    assert body["status"] == "正常"

    rows = client.get("/api/shipper/warehouses").json()
    assert len(rows) == 1
    assert rows[0]["name"] == "华东二号仓"
    assert "科苑路 200 号" in rows[0]["location"]


def test_disable_warehouse_removes_it_from_new_order_sources(client):
    """停用后仓库仍在列表，但不出现在可用（正常）发货仓库中。"""
    reg = _register(client, "wh1")
    csrf = _csrf(reg)
    created = _create(client, csrf).json()

    resp = client.post(
        f"/api/shipper/warehouses/{created['id']}/disable", headers=csrf
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "停用"

    all_rows = client.get("/api/shipper/warehouses").json()
    assert [row["status"] for row in all_rows] == ["停用"]
    available = client.get(
        "/api/shipper/warehouses", params={"status": "正常"}
    ).json()
    assert available == []
    disabled = client.get(
        "/api/shipper/warehouses", params={"status": "停用"}
    ).json()
    assert [row["id"] for row in disabled] == [created["id"]]


def test_disabled_warehouse_can_be_enabled_again(client):
    """停用后再启用，恢复为正常并重新成为可用发货仓库。"""
    reg = _register(client, "wh1")
    csrf = _csrf(reg)
    created = _create(client, csrf).json()
    wid = created["id"]

    assert client.post(f"/api/shipper/warehouses/{wid}/disable", headers=csrf).json()[
        "status"
    ] == "停用"
    resp = client.post(f"/api/shipper/warehouses/{wid}/enable", headers=csrf)
    assert resp.status_code == 200
    assert resp.json()["status"] == "正常"
    assert len(client.get("/api/shipper/warehouses", params={"status": "正常"}).json()) == 1


def test_warehouse_changes_do_not_rewrite_existing_orders(client):
    """仓库改名 / 改址 / 停用后，既有运输订单字段保持原样。"""
    import sqlite3

    reg = _register(client, "wh1")
    csrf = _csrf(reg)
    wid = _create(client, csrf).json()["id"]

    # 直接在此布置一条历史订单，断言仍全部经 HTTP 读取
    shipper_id = client.get("/api/auth/me").json()["id"]
    conn = sqlite3.connect(client.app.state.settings.db_path)
    conn.execute(
        """INSERT INTO orders (order_no, shipper_id, cargo_name, status, created_at)
           VALUES (?, ?, ?, '待承接', ?)""",
        ("ORD-261122-0001", shipper_id, "原货物", "2026-11-22T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()
    original = client.get("/api/shipper/orders").json()[0]

    assert (
        client.put(
            f"/api/shipper/warehouses/{wid}",
            json=_warehouse_body(name="改名后的仓库", detail_address="新地址 999 号"),
            headers=csrf,
        ).status_code
        == 200
    )
    assert client.post(f"/api/shipper/warehouses/{wid}/disable", headers=csrf).status_code == 200

    orders = client.get("/api/shipper/orders").json()
    assert len(orders) == 1
    for key in ("id", "order_no", "cargo_name", "status", "created_at"):
        assert orders[0][key] == original[key]


# --- slice 3: 权限隔离、CSRF 与输入校验 ---


def test_other_shipper_cannot_read_or_mutate_warehouse(client):
    """货主只能管理自己的仓库，越权读写返回 404 且不泄露他人数据。"""
    reg1 = _register(client, "wh1")
    wid = _create(client, _csrf(reg1)).json()["id"]

    reg2 = _register(client, "wh2")
    csrf2 = _csrf(reg2)
    assert client.get("/api/shipper/warehouses").json() == []
    assert client.get("/api/shipper/warehouses", params={"name": "华东"}).json() == []

    for resp in (
        client.put(
            f"/api/shipper/warehouses/{wid}", json=_warehouse_body(), headers=csrf2
        ),
        client.post(f"/api/shipper/warehouses/{wid}/disable", headers=csrf2),
        client.post(f"/api/shipper/warehouses/{wid}/enable", headers=csrf2),
    ):
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "仓库不存在"


def test_non_shipper_cannot_access_warehouses(client):
    """非货主角色访问仓库接口返回 404。"""
    admin = client.post(
        "/api/auth/login", json={"phone": "admin", "password": "admin123456"}
    )
    admin_csrf = _csrf(admin)
    assert client.get("/api/shipper/warehouses").status_code == 404
    assert (
        client.post(
            "/api/shipper/warehouses", json=_warehouse_body(), headers=admin_csrf
        ).status_code
        == 404
    )


def test_warehouse_writes_require_csrf(client):
    """创建、修改、停用均为写操作，缺 CSRF 头返回 403。"""
    reg = _register(client, "wh1")
    wid = _create(client, _csrf(reg)).json()["id"]
    assert (
        client.post("/api/shipper/warehouses", json=_warehouse_body()).status_code == 403
    )
    assert (
        client.put(
            f"/api/shipper/warehouses/{wid}", json=_warehouse_body()
        ).status_code
        == 403
    )
    assert client.post(f"/api/shipper/warehouses/{wid}/disable").status_code == 403


def test_warehouse_create_validates_input(client):
    """必填字段、长度与未知字段均在边界校验。"""
    reg = _register(client, "wh1")
    csrf = _csrf(reg)
    assert (
        client.post("/api/shipper/warehouses", json={"name": "只有名称"}, headers=csrf).status_code
        == 422
    )
    assert (
        client.post(
            "/api/shipper/warehouses", json=_warehouse_body(name=""), headers=csrf
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/shipper/warehouses",
            json=_warehouse_body(unknown_field="x"),
            headers=csrf,
        ).status_code
        == 422
    )
    assert client.get("/api/shipper/warehouses").json() == []


def test_like_wildcards_are_literal_in_name_search(client):
    """名称搜索把 % 与 _ 当作字面字符，不被当成通配符。"""
    reg = _register(client, "wh1")
    csrf = _csrf(reg)
    assert _create(client, csrf, name="A%B仓").status_code == 201
    assert _create(client, csrf, name="AXB仓").status_code == 201
    rows = client.get("/api/shipper/warehouses", params={"name": "%"}).json()
    assert [row["name"] for row in rows] == ["A%B仓"]
