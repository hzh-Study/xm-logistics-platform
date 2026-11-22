"""货主认证 seam 测试：注册、资料提交、审核、驳回重提、发布阻断与状态正交。"""

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

ADMIN = ("admin", "admin123456")
PW = "pw123456"


def _register(client: TestClient, phone: str, password: str = PW):
    """经注册接口创建货主并登录。"""
    return client.post(
        "/api/shipper/register",
        json={"phone": phone, "password": password},
    )


def _login(client: TestClient, phone: str, password: str):
    """经登录接口取 token 与 CSRF。"""
    return client.post(
        "/api/auth/login",
        json={"phone": phone, "password": password},
    )


def _csrf(resp) -> dict:
    """从登录 / 注册响应取写操作所需的 CSRF 头。"""
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _submit(client: TestClient, csrf: dict, **overrides):
    """提交认证资料，默认个人认证。"""
    body = {
        "cert_type": "个人",
        "name": "张三",
        "id_number": "110101199001011234",
        "contact_phone": "13900000000",
        "documents": ["certs/id-front.png", "certs/id-back.png"],
    }
    body.update(overrides)
    return client.post("/api/shipper/certification", json=body, headers=csrf)


def _submit_enterprise(client: TestClient, csrf: dict):
    """提交企业认证资料。"""
    return _submit(
        client,
        csrf,
        cert_type="企业",
        name="顺达物流有限公司",
        id_number="91310100MA1K1234X9",
        contact_phone="021-88888888",
        documents=["certs/license.png", "certs/legal-id.png"],
    )


def _as_admin(client: TestClient) -> dict:
    """登录管理员并返回 CSRF 头。"""
    resp = _login(client, *ADMIN)
    assert resp.status_code == 200
    return _csrf(resp)


# --- slice 1: 注册与初始认证状态 ---


def test_shipper_can_register_and_access_workspace(client):
    """货主可用手机号注册，进入货主工作台，初始认证状态为未提交。"""
    resp = _register(client, "shipper1")
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["role"] == "货主"
    assert body["user"]["account_status"] == "正常使用"
    assert body["user"]["auth_status"] == "未提交"
    assert "csrf_token" in body
    assert client.cookies.get("session_token")
    assert client.get("/api/shipper/workbench").status_code == 200


def test_fresh_shipper_certification_is_unsubmitted(client):
    """新注册货主查看认证状态为未提交，且无认证资料。"""
    _register(client, "shipper1")
    resp = client.get("/api/shipper/certification")
    assert resp.status_code == 200
    body = resp.json()
    assert body["auth_status"] == "未提交"
    assert body["current"] is None
    assert body["history"] == []


def test_duplicate_phone_registration_rejected(client):
    """同一手机号不能重复注册。"""
    assert _register(client, "shipper1").status_code == 201
    assert _register(client, "shipper1").status_code == 409


# --- slice 2: 资料提交 ---


def test_shipper_submits_personal_certification(client):
    """货主提交个人认证资料后状态转为待审核，资料可按接口读回。"""
    reg = _register(client, "shipper1")
    assert _submit(client, _csrf(reg)).status_code == 201
    me = client.get("/api/auth/me")
    assert me.json()["auth_status"] == "待审核"
    view = client.get("/api/shipper/certification").json()
    assert view["auth_status"] == "待审核"
    current = view["current"]
    assert current["cert_type"] == "个人"
    assert current["name"] == "张三"
    assert current["id_number"] == "110101199001011234"
    assert current["contact_phone"] == "13900000000"
    assert current["documents"] == ["certs/id-front.png", "certs/id-back.png"]
    assert current["status"] == "待审核"
    assert current["rejection_reason"] is None
    assert current["reviewed_at"] is None
    assert len(view["history"]) == 1


def test_shipper_submits_enterprise_certification(client):
    """货主可提交企业认证资料并按接口读回。"""
    reg = _register(client, "shipper1")
    assert _submit_enterprise(client, _csrf(reg)).status_code == 201
    view = client.get("/api/shipper/certification").json()
    assert view["auth_status"] == "待审核"
    current = view["current"]
    assert current["cert_type"] == "企业"
    assert current["name"] == "顺达物流有限公司"
    assert current["id_number"] == "91310100MA1K1234X9"
    assert current["documents"] == ["certs/license.png", "certs/legal-id.png"]


def test_certification_submission_requires_csrf(client):
    """提交认证资料是写操作，缺 CSRF 头返回 403。"""
    _register(client, "shipper1")
    assert client.post(
        "/api/shipper/certification",
        json={
            "cert_type": "个人",
            "name": "张三",
            "id_number": "110101199001011234",
            "contact_phone": "13900000000",
            "documents": [],
        },
    ).status_code == 403


def test_certification_rejects_absolute_document_path(client):
    """资料路径必须是库内相对路径，绝对路径返回校验错误。"""
    reg = _register(client, "shipper1")
    resp = _submit(client, _csrf(reg), documents=["/etc/passwd"])
    assert resp.status_code == 422
    assert client.get("/api/shipper/certification").json()["auth_status"] == "未提交"


def test_cannot_resubmit_while_pending(client):
    """审核中不允许重复提交认证资料。"""
    reg = _register(client, "shipper1")
    csrf = _csrf(reg)
    assert _submit(client, csrf).status_code == 201
    assert _submit(client, csrf).status_code == 409


# --- slice 3: 管理员审核、驳回原因与重提 ---


def _latest_cert_id(client: TestClient, admin_csrf: dict) -> int:
    """从管理员列表接口取最新一条货主认证提交 id。"""
    resp = client.get("/api/admin/shipper-certifications")
    assert resp.status_code == 200
    rows = resp.json()
    assert rows
    return rows[0]["certification_id"]


def _review(client: TestClient, admin_csrf: dict, cert_id: int, **body):
    """管理员审核指定认证提交。"""
    payload = {"decision": "审核通过"}
    payload.update(body)
    return client.post(
        f"/api/admin/shipper-certifications/{cert_id}/review",
        json=payload,
        headers=admin_csrf,
    )


def test_admin_lists_pending_shipper_certifications(client):
    """管理员可列出待审核货主认证及资料。"""
    reg = _register(client, "shipper1")
    _submit(client, _csrf(reg))
    admin_csrf = _as_admin(client)
    rows = client.get("/api/admin/shipper-certifications").json()
    assert len(rows) == 1
    row = rows[0]
    assert row["phone"] == "shipper1"
    assert row["cert_type"] == "个人"
    assert row["name"] == "张三"
    assert row["status"] == "待审核"
    assert row["documents"] == ["certs/id-front.png", "certs/id-back.png"]
    assert row["auth_status"] == "待审核"


def test_admin_can_approve_certification(client):
    """管理员审核通过后货主认证状态变为审核通过。"""
    reg = _register(client, "shipper1")
    _submit(client, _csrf(reg))
    admin_csrf = _as_admin(client)
    cert_id = _latest_cert_id(client, admin_csrf)
    resp = _review(client, admin_csrf, cert_id)
    assert resp.status_code == 200
    assert resp.json()["status"] == "审核通过"
    _login(client, "shipper1", PW)
    view = client.get("/api/shipper/certification").json()
    assert view["auth_status"] == "审核通过"
    assert view["current"]["status"] == "审核通过"
    assert view["current"]["reviewer_id"] is not None
    assert view["current"]["reviewed_at"] is not None


def test_admin_reject_requires_reason(client):
    """驳回原因必填：缺原因返回校验错误且不改变认证状态。"""
    reg = _register(client, "shipper1")
    _submit(client, _csrf(reg))
    admin_csrf = _as_admin(client)
    cert_id = _latest_cert_id(client, admin_csrf)
    resp = _review(client, admin_csrf, cert_id, decision="审核不通过")
    assert resp.status_code == 422
    assert "驳回原因" in resp.json()["error"]["details"][0]["message"]
    rows = client.get("/api/admin/shipper-certifications").json()
    assert rows[0]["auth_status"] == "待审核"
    assert rows[0]["status"] == "待审核"


def test_rejection_reason_visible_to_shipper(client):
    """驳回原因对货主可见，账号状态仍为正常使用。"""
    reg = _register(client, "shipper1")
    _submit(client, _csrf(reg))
    admin_csrf = _as_admin(client)
    cert_id = _latest_cert_id(client, admin_csrf)
    resp = _review(
        client,
        admin_csrf,
        cert_id,
        decision="审核不通过",
        rejection_reason="身份证照片模糊，请重新上传",
    )
    assert resp.status_code == 200
    assert resp.json()["rejection_reason"] == "身份证照片模糊，请重新上传"
    _login(client, "shipper1", PW)
    view = client.get("/api/shipper/certification").json()
    assert view["auth_status"] == "审核不通过"
    assert view["current"]["status"] == "审核不通过"
    assert view["current"]["rejection_reason"] == "身份证照片模糊，请重新上传"
    me = client.get("/api/auth/me").json()
    assert me["auth_status"] == "审核不通过"
    assert me["account_status"] == "正常使用"


def test_shipper_resubmits_after_rejection(client):
    """驳回后重新提交：状态回到待审核，原驳回记录仍在历史中。"""
    reg = _register(client, "shipper1")
    csrf = _csrf(reg)
    _submit(client, csrf)
    admin_csrf = _as_admin(client)
    cert_id = _latest_cert_id(client, admin_csrf)
    assert _review(
        client,
        admin_csrf,
        cert_id,
        decision="审核不通过",
        rejection_reason="请补交营业执照",
    ).status_code == 200
    _login(client, "shipper1", PW)
    csrf = {"X-CSRF-Token": client.get("/api/auth/me").json()["csrf_token"]}
    assert _submit(client, csrf, documents=["certs/new-id.png"]).status_code == 201
    view = client.get("/api/shipper/certification").json()
    assert view["auth_status"] == "待审核"
    assert len(view["history"]) == 2
    assert view["current"]["status"] == "待审核"
    assert view["current"]["documents"] == ["certs/new-id.png"]
    old = view["history"][1]
    assert old["status"] == "审核不通过"
    assert old["rejection_reason"] == "请补交营业执照"


def test_notifications_recorded_on_review(client):
    """审核通过与驳回各落一条对应货主收件通知。"""
    reg1 = _register(client, "shipper1")
    _submit(client, _csrf(reg1))
    admin_csrf = _as_admin(client)
    cert1 = _latest_cert_id(client, admin_csrf)
    assert _review(client, admin_csrf, cert1).status_code == 200

    reg2 = _register(client, "shipper2")
    _submit(client, _csrf(reg2))
    admin_csrf = _as_admin(client)
    rows = client.get("/api/admin/shipper-certifications").json()
    cert2 = next(r["certification_id"] for r in rows if r["phone"] == "shipper2")
    assert (
        _review(
            client,
            admin_csrf,
            cert2,
            decision="审核不通过",
            rejection_reason="资料过期",
        ).status_code
        == 200
    )

    _login(client, "shipper1", PW)
    notes1 = client.get("/api/shipper/notifications").json()
    assert len(notes1) == 1
    assert notes1[0]["kind"] in ("认证审核通过", "认证通过")
    assert notes1[0]["related_id"] == cert1

    _login(client, "shipper2", PW)
    notes2 = client.get("/api/shipper/notifications").json()
    assert len(notes2) == 1
    assert notes2[0]["kind"] in ("认证驳回", "认证审核不通过")
    assert "资料过期" in notes2[0]["body"]
    assert notes2[0]["related_id"] == cert2


def test_already_reviewed_certification_cannot_be_reviewed_again(client):
    """同一认证提交不能重复审核，更正须由货主重新提交。"""
    reg = _register(client, "shipper1")
    _submit(client, _csrf(reg))
    admin_csrf = _as_admin(client)
    cert_id = _latest_cert_id(client, admin_csrf)
    assert _review(client, admin_csrf, cert_id).status_code == 200
    assert _review(client, admin_csrf, cert_id).status_code == 409


def test_shipper_cannot_use_admin_review_endpoint(client):
    """货主不能调用管理员审核接口。"""
    reg = _register(client, "shipper1")
    _submit(client, _csrf(reg))
    resp = client.post(
        "/api/admin/shipper-certifications/1/review",
        json={"decision": "审核通过"},
        headers=_csrf(reg),
    )
    assert resp.status_code == 404


# --- slice 4: 发布门禁、状态正交与隔离 ---


def _publish(client: TestClient, csrf: dict, cargo: str = "钢材"):
    """尝试发布运输订单。"""
    return client.post(
        "/api/shipper/orders", json={"cargo_name": cargo}, headers=csrf
    )


def test_publish_blocked_without_certification(client):
    """未提交认证时发布被阻断并给出明确原因。"""
    reg = _register(client, "shipper1")
    resp = _publish(client, _csrf(reg))
    assert resp.status_code == 403
    message = resp.json()["error"]["message"]
    assert "认证" in message or "审核通过" in message
    assert client.get("/api/shipper/orders").json() == []


def test_publish_blocked_while_pending(client):
    """审核中发布被阻断。"""
    reg = _register(client, "shipper1")
    csrf = _csrf(reg)
    _submit(client, csrf)
    assert _publish(client, csrf).status_code == 403


def test_publish_blocked_after_rejection(client):
    """驳回后发布仍被阻断。"""
    reg = _register(client, "shipper1")
    csrf = _csrf(reg)
    _submit(client, csrf)
    admin_csrf = _as_admin(client)
    cert_id = _latest_cert_id(client, admin_csrf)
    _review(
        client,
        admin_csrf,
        cert_id,
        decision="审核不通过",
        rejection_reason="资料不全",
    )
    _login(client, "shipper1", PW)
    csrf = {"X-CSRF-Token": client.get("/api/auth/me").json()["csrf_token"]}
    assert _publish(client, csrf).status_code == 403


def test_publish_allowed_after_approval_with_order_no(client):
    """审核通过后发布成功，订单进入待承接并生成日期序列订单号。"""
    import re

    reg = _register(client, "shipper1")
    csrf = _csrf(reg)
    _submit(client, csrf)
    admin_csrf = _as_admin(client)
    cert_id = _latest_cert_id(client, admin_csrf)
    assert _review(client, admin_csrf, cert_id).status_code == 200
    _login(client, "shipper1", PW)
    csrf = {"X-CSRF-Token": client.get("/api/auth/me").json()["csrf_token"]}

    first = _publish(client, csrf, "钢材")
    assert first.status_code == 201
    body = first.json()
    assert body["status"] == "待承接"
    assert body["cargo_name"] == "钢材"
    assert re.match(r"^ORD-\d{6}-\d{4}$", body["order_no"])
    assert body["order_no"].endswith("-0001")

    second = _publish(client, csrf, "水泥")
    assert second.status_code == 201
    assert second.json()["order_no"].endswith("-0002")

    orders = client.get("/api/shipper/orders").json()
    assert [o["order_no"] for o in orders] == [
        second.json()["order_no"],
        body["order_no"],
    ]


def test_auth_status_independent_of_account_status(client):
    """禁用账号不改写认证记录与认证状态，且即时阻断会话。"""
    reg = _register(client, "shipper1")
    _submit(client, _csrf(reg))
    admin_csrf = _as_admin(client)
    cert_id = _latest_cert_id(client, admin_csrf)
    _review(client, admin_csrf, cert_id)

    _login(client, "shipper1", PW)
    assert client.get("/api/shipper/workbench").status_code == 200

    conn = sqlite3.connect(client.app.state.settings.db_path)
    conn.execute("UPDATE accounts SET account_status = '已禁用' WHERE phone = 'shipper1'")
    conn.commit()
    conn.close()

    assert client.get("/api/shipper/workbench").status_code == 403
    assert client.get("/api/shipper/certification").status_code == 403

    _as_admin(client)
    rows = client.get("/api/admin/shipper-certifications").json()
    row = next(r for r in rows if r["phone"] == "shipper1")
    assert row["account_status"] == "已禁用"
    assert row["auth_status"] == "审核通过"
    assert row["certification_id"] == cert_id
    assert row["status"] == "审核通过"


def test_shippers_isolated_from_each_other(client):
    """货主只能看到自己的通知与订单。"""
    reg1 = _register(client, "shipper1")
    csrf1 = _csrf(reg1)
    _submit(client, csrf1)
    admin_csrf = _as_admin(client)
    rows = client.get("/api/admin/shipper-certifications").json()
    cert_id = next(r["certification_id"] for r in rows if r["phone"] == "shipper1")
    _review(client, admin_csrf, cert_id)

    _login(client, "shipper1", PW)
    csrf1 = {"X-CSRF-Token": client.get("/api/auth/me").json()["csrf_token"]}
    assert _publish(client, csrf1).status_code == 201

    reg2 = _register(client, "shipper2")
    csrf2 = _csrf(reg2)
    _submit(client, csrf2)
    admin_csrf = _as_admin(client)
    rows = client.get("/api/admin/shipper-certifications").json()
    cert2 = next(r["certification_id"] for r in rows if r["phone"] == "shipper2")
    _review(client, admin_csrf, cert2)

    _login(client, "shipper2", PW)
    assert client.get("/api/shipper/orders").json() == []
    notes = client.get("/api/shipper/notifications").json()
    assert len(notes) == 1
    assert notes[0]["related_id"] == cert2
