"""物流公司认证与审核 seam 测试：注册、资料提交、审核、驳回重提与业务阻断。"""

from fastapi.testclient import TestClient

SEED_ADMIN = ("admin", "admin123456")


def _login(client: TestClient, phone: str, password: str = "pw123456"):
    """经真实登录接口取 token 与 CSRF。"""
    return client.post("/api/auth/login", json={"phone": phone, "password": password})


def _csrf(resp) -> dict:
    """从登录响应取 CSRF 头，供写操作使用。"""
    return {"X-CSRF-Token": resp.json()["csrf_token"]}


def _register_carrier(
    client: TestClient,
    phone: str = "carrier1",
    company: str = "顺达物流有限公司",
    password: str = "pw123456",
):
    """经注册接口创建物流公司账号。"""
    return client.post(
        "/api/carrier/register",
        json={"phone": phone, "password": password, "company_name": company},
    )


def test_carrier_can_register_and_login(client):
    """物流公司注册后账号状态正常、认证状态为未提交，可用口令登录。"""
    reg = _register_carrier(client)
    assert reg.status_code == 201
    body = reg.json()
    assert body["role"] == "物流公司"
    assert body["account_status"] == "正常使用"
    assert body["auth_status"] == "未提交"

    login = _login(client, "carrier1")
    assert login.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["auth_status"] == "未提交"


def test_duplicate_phone_registration_rejected(client):
    """重复手机号注册返回 409，不新建账号。"""
    assert _register_carrier(client, phone="carrier-dup").status_code == 201
    second = _register_carrier(client, phone="carrier-dup", company="另一家公司")
    assert second.status_code == 409
    assert "error" in second.json()


CERT_PAYLOAD = {
    "company_name": "顺达物流有限公司",
    "license_no": "91310000MA1FL1234X",
    "license_path": "credentials/carrier/license.png",
    "legal_person": "张三",
    "contact_name": "李四",
    "contact_phone": "13900000000",
    "qualification_path": "credentials/carrier/qualification.pdf",
    "note": "首次提交",
}


def _submit_cert(client: TestClient, csrf: dict, **overrides):
    """经接口提交企业认证资料。"""
    return client.post(
        "/api/carrier/certification",
        json={**CERT_PAYLOAD, **overrides},
        headers=csrf,
    )


def _login_carrier(client: TestClient, phone: str = "carrier1"):
    """注册并登录物流公司，返回登录响应。"""
    _register_carrier(client, phone=phone)
    return _login(client, phone)


def test_carrier_can_submit_certification_and_read_status(client):
    """物流公司提交企业认证资料后，认证状态变为待审核且资料可读。"""
    login = _login_carrier(client)
    submitted = _submit_cert(client, _csrf(login))
    assert submitted.status_code == 201

    view = client.get("/api/carrier/certification")
    assert view.status_code == 200
    body = view.json()
    assert body["auth_status"] == "待审核"
    assert len(body["records"]) == 1
    latest = body["latest"]
    assert latest["company_name"] == CERT_PAYLOAD["company_name"]
    assert latest["license_no"] == CERT_PAYLOAD["license_no"]
    assert latest["legal_person"] == CERT_PAYLOAD["legal_person"]
    assert latest["contact_phone"] == CERT_PAYLOAD["contact_phone"]
    assert latest["kind"] == "提交"


def test_certification_submission_requires_complete_fields(client):
    """认证资料缺营业执照号时参数校验失败，状态不变。"""
    login = _login_carrier(client)
    payload = dict(CERT_PAYLOAD)
    payload.pop("license_no")
    resp = client.post(
        "/api/carrier/certification", json=payload, headers=_csrf(login)
    )
    assert resp.status_code == 422
    assert client.get("/api/carrier/certification").json()["auth_status"] == "未提交"


def test_certification_write_requires_csrf(client):
    """认证提交是写操作，缺 CSRF token 返回 403。"""
    _login_carrier(client)
    assert client.post("/api/carrier/certification", json=CERT_PAYLOAD).status_code == 403


def test_carrier_business_blocked_before_and_during_review(client):
    """未提交与待审核阶段，承接/派单等承运业务入口被阻断且原因明确。"""
    login = _login_carrier(client)

    entry = client.get("/api/carrier/business-access")
    assert entry.status_code == 403
    assert "认证" in entry.json()["error"]["message"]

    caps = client.get("/api/carrier/capabilities")
    assert caps.status_code == 200
    body = caps.json()
    assert body["can_accept_orders"] is False
    assert body["can_dispatch"] is False
    assert body["can_manage_drivers"] is False
    assert body["can_manage_vehicles"] is False
    assert body["reasons"]

    _submit_cert(client, _csrf(login))
    assert client.get("/api/carrier/business-access").status_code == 403


def _admin_login(client: TestClient):
    """登录种子管理员。"""
    return _login(client, *SEED_ADMIN)


def _review(client: TestClient, csrf: dict, account_id: int, decision: str, reason: str = ""):
    """管理员审核指定物流公司的认证。"""
    return client.post(
        f"/api/admin/carrier-certifications/{account_id}/review",
        json={"decision": decision, "reason": reason},
        headers=csrf,
    )


def test_admin_approval_opens_carrier_business(client):
    """管理员审核通过后，物流公司认证状态更新且可进入承运业务。"""
    login = _login_carrier(client)
    account_id = login.json()["user"]["id"]
    _submit_cert(client, _csrf(login))

    review = _review(client, _csrf(_admin_login(client)), account_id, "通过")
    assert review.status_code == 200

    _login(client, "carrier1")
    view = client.get("/api/carrier/certification").json()
    assert view["auth_status"] == "审核通过"
    assert view["latest"]["kind"] == "审核"
    assert view["latest"]["decision"] == "通过"
    assert client.get("/api/carrier/business-access").status_code == 200
    caps = client.get("/api/carrier/capabilities").json()
    assert all(
        caps[key] is True
        for key in (
            "can_accept_orders", "can_dispatch",
            "can_manage_drivers", "can_manage_vehicles",
        )
    )


def test_admin_rejection_requires_reason(client):
    """管理员驳回必须填写原因，否则 422。"""
    login = _login_carrier(client)
    account_id = login.json()["user"]["id"]
    _submit_cert(client, _csrf(login))

    bad = _review(client, _csrf(_admin_login(client)), account_id, "驳回")
    assert bad.status_code == 422
    assert "error" in bad.json()


def test_carrier_sees_rejection_reason_and_resubmits(client):
    """驳回原因对公司可见，公司可重新提交，原始提交记录仍保留。"""
    login = _login_carrier(client)
    account_id = login.json()["user"]["id"]
    _submit_cert(client, _csrf(login))

    admin_csrf = _csrf(_admin_login(client))
    rejected = _review(client, admin_csrf, account_id, "驳回", "营业执照不清晰，请重新上传")
    assert rejected.status_code == 200

    _login(client, "carrier1")
    view = client.get("/api/carrier/certification").json()
    assert view["auth_status"] == "审核不通过"
    assert view["latest"]["kind"] == "审核"
    assert view["latest"]["decision"] == "驳回"
    assert "营业执照" in view["latest"]["reason"]
    assert client.get("/api/carrier/business-access").status_code == 403

    resubmit = _submit_cert(client, _csrf(_login(client, "carrier1")), note="重新提交")
    assert resubmit.status_code == 201
    view = client.get("/api/carrier/certification").json()
    assert view["auth_status"] == "待审核"
    assert len(view["records"]) == 3
    assert [r["kind"] for r in view["records"]] == ["提交", "审核", "提交"]
    assert view["records"][0]["note"] == "首次提交"
    assert view["records"][0]["reason"] == ""


def test_non_admin_cannot_review(client):
    """物流公司角色调用管理员审核接口返回 404。"""
    login = _login_carrier(client)
    account_id = login.json()["user"]["id"]
    resp = _review(client, _csrf(login), account_id, "通过")
    assert resp.status_code == 404


def _set_account_status(client: TestClient, csrf: dict, account_id: int, value: str):
    """管理员设置物流公司账号状态。"""
    return client.post(
        f"/api/admin/carriers/{account_id}/status",
        json={"account_status": value},
        headers=csrf,
    )


def _admin_session(client: TestClient):
    """独立管理员会话，避免覆盖物流公司会话 cookie。"""
    admin = TestClient(client.app)
    csrf = _csrf(_login(admin, *SEED_ADMIN))
    return admin, csrf


def test_admin_disable_and_restore_carrier(client):
    """管理员禁用立即阻断承运业务并失效会话，恢复后重新可用。"""
    login = _login_carrier(client)
    account_id = login.json()["user"]["id"]
    _submit_cert(client, _csrf(login))
    admin, admin_csrf = _admin_session(client)
    assert _review(admin, admin_csrf, account_id, "通过").status_code == 200

    assert client.get("/api/carrier/business-access").status_code == 200
    disabled = _set_account_status(admin, admin_csrf, account_id, "已禁用")
    assert disabled.status_code == 200
    assert disabled.json()["account_status"] == "已禁用"

    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/carrier/business-access").status_code == 401
    assert _login(client, "carrier1").status_code == 403

    restored = _set_account_status(admin, admin_csrf, account_id, "正常使用")
    assert restored.status_code == 200
    assert _login(client, "carrier1").status_code == 200
    assert client.get("/api/carrier/business-access").status_code == 200


def test_admin_lists_carriers_and_filters_by_auth_status(client):
    """管理员可列出物流公司并按认证状态筛选。"""
    login = _login_carrier(client)
    account_id = login.json()["user"]["id"]
    _submit_cert(client, _csrf(login))
    admin_csrf = _csrf(_admin_login(client))

    listed = client.get("/api/admin/carriers")
    assert listed.status_code == 200
    assert any(item["account_id"] == account_id for item in listed.json())
    item = next(item for item in listed.json() if item["account_id"] == account_id)
    assert item["auth_status"] == "待审核"
    assert item["company_name"] == CERT_PAYLOAD["company_name"]

    pending = client.get("/api/admin/carriers", params={"auth_status": "审核通过"})
    assert all(row["auth_status"] == "审核通过" for row in pending.json())


def test_certification_history_is_append_only(client):
    """多轮提交与审核后，全部记录经接口仍可读，原记录未被覆盖。"""
    login = _login_carrier(client)
    account_id = login.json()["user"]["id"]
    _submit_cert(client, _csrf(login), note="第一轮")
    admin_csrf = _csrf(_admin_login(client))
    _review(client, admin_csrf, account_id, "通过")

    _login(client, "carrier1")
    _submit_cert(client, _csrf(_login(client, "carrier1")), note="第二轮")
    admin_csrf = _csrf(_admin_login(client))
    _review(client, admin_csrf, account_id, "驳回", "资质文件过期")

    history = client.get(f"/api/admin/carriers/{account_id}/certifications").json()
    assert len(history) == 4
    assert [r["kind"] for r in history] == ["提交", "审核", "提交", "审核"]
    assert [r["decision"] for r in history] == ["", "通过", "", "驳回"]
    assert [r["actor"] for r in history] == [
        "物流公司", "管理员", "物流公司", "管理员",
    ]
    assert history[0]["note"] == "第一轮"
    assert history[2]["note"] == "第二轮"
    assert history[3]["reason"] == "资质文件过期"
    assert all("T" in r["created_at"] for r in history)


def test_review_unknown_carrier_returns_404(client):
    """审核不存在的物流公司返回 404。"""
    admin_csrf = _csrf(_admin_login(client))
    assert _review(client, admin_csrf, 999999, "通过").status_code == 404


def test_carrier_certification_endpoints_are_role_isolated(client):
    """非物流公司角色访问物流公司认证接口返回 404。"""
    _admin_login(client)
    assert client.get("/api/carrier/certification").status_code == 404
    assert client.get("/api/carrier/capabilities").status_code == 404


def test_review_rejects_unknown_decision(client):
    """审核结论只能是通过或驳回。"""
    login = _login_carrier(client)
    account_id = login.json()["user"]["id"]
    resp = _review(client, _csrf(_admin_login(client)), account_id, "待定")
    assert resp.status_code == 422


def test_registration_rejects_short_password(client):
    """注册口令过短被拒绝。"""
    resp = _register_carrier(client, phone="short-pw", password="123")
    assert resp.status_code == 422
