"""认证接口用例（05 文档 3.2 #1–#6、#12）。测试只用 @example.com 域。"""
from tests.conftest import WHITELIST_EMAIL, add_whitelist, register_and_activate, staff_login


def _reg(client, email="student@example.com", name="同学", password="Passw0rd!"):
    return client.post(
        "/api/auth/register", json={"email": email, "name": name, "password": password}
    )


# #1 非白名单邮箱注册 → 403 EMAIL_NOT_WHITELISTED
def test_register_not_whitelisted(client):
    r = _reg(client, "stranger@example.com")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "EMAIL_NOT_WHITELISTED"


# #2 白名单邮箱重复注册 → 409 EMAIL_TAKEN
def test_register_email_taken(client, db):
    add_whitelist(db)
    assert _reg(client).status_code == 200
    r = _reg(client)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "EMAIL_TAKEN"


def test_register_weak_password(client, db):
    add_whitelist(db)
    r = _reg(client, password="short")
    assert r.status_code == 400


# #3 未激活账号登录 → 403 ACCOUNT_PENDING（不提示密码错）
def test_login_pending_account(client, db):
    add_whitelist(db)
    _reg(client)
    r = client.post(
        "/api/auth/login", json={"email": WHITELIST_EMAIL, "password": "Passw0rd!"}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ACCOUNT_PENDING"


# #4 连续 5 次密码错 → 第 6 次 429 ACCOUNT_LOCKED
def test_login_lock_after_5_failures(client, db):
    add_whitelist(db)
    register_and_activate(client, db)
    for _ in range(5):
        r = client.post(
            "/api/auth/login", json={"email": WHITELIST_EMAIL, "password": "WrongPass1"}
        )
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"
    r = client.post(
        "/api/auth/login", json={"email": WHITELIST_EMAIL, "password": "WrongPass1"}
    )
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "ACCOUNT_LOCKED"


def test_login_success_after_activation(client, db):
    add_whitelist(db)
    token, _ = register_and_activate(client, db)
    r = client.post(
        "/api/auth/login", json={"email": WHITELIST_EMAIL, "password": "Passw0rd!"}
    )
    assert r.status_code == 200
    assert r.json()["token"]
    assert r.json()["student"]["cohort"] == "202610 期"
    assert r.json()["student"]["cohort_start_date"] == "2026-10-01"


# #5 verify token 用过一次再用 → 400 TOKEN_INVALID（一次性）
def test_verify_token_single_use(client, db):
    from app.models import EmailToken, Student

    add_whitelist(db)
    _reg(client)
    row = (
        db.query(EmailToken)
        .join(Student, EmailToken.student_id == Student.id)
        .filter(Student.email == WHITELIST_EMAIL)
        .one()
    )
    first = client.post(f"/api/auth/verify/{row.token}")
    assert first.status_code == 200
    second = client.post(f"/api/auth/verify/{row.token}")
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "TOKEN_INVALID"


# #6 verify token 过 24h → 400 TOKEN_EXPIRED
def test_verify_token_expired(client, db):
    from datetime import timedelta

    from app.models import EmailToken, Student
    from app.timeutil import now_utc

    add_whitelist(db)
    _reg(client)
    row = (
        db.query(EmailToken)
        .join(Student, EmailToken.student_id == Student.id)
        .filter(Student.email == WHITELIST_EMAIL)
        .one()
    )
    row.expires_at = now_utc() - timedelta(seconds=1)
    db.commit()
    r = client.post(f"/api/auth/verify/{row.token}")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "TOKEN_EXPIRED"


# #13（单元层）magic_link 过 7 天 → 拒绝
def test_magic_link_expired(client, db):
    from datetime import timedelta

    from app.models import EmailToken
    from app.timeutil import now_utc

    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    token = EmailToken(
        student_id=student_id,
        token="expired-magic-token",
        purpose="magic_link",
        expires_at=now_utc() - timedelta(seconds=1),
    )
    db.add(token)
    db.commit()
    r = client.get("/api/links/magic/expired-magic-token")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "TOKEN_EXPIRED"


# #12 学员 token 访问 /admin/* → 403 FORBIDDEN
def test_student_token_forbidden_on_admin(client, db):
    add_whitelist(db)
    token, _ = register_and_activate(client, db)
    r = client.get("/api/admin/students", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_staff_token_forbidden_on_student_api(client, db):
    staff_token = staff_login(client)
    r = client.get("/api/overview", headers={"Authorization": f"Bearer {staff_token}"})
    assert r.status_code in (401, 403)


def test_resend_verification_no_existence_leak(client, db):
    add_whitelist(db)
    _reg(client)
    r = client.post("/api/auth/resend-verification", json={"email": "unknown@example.com"})
    assert r.status_code == 200


def test_forgot_reset_password_flow(client, db):
    from app.models import EmailToken, Student

    add_whitelist(db)
    register_and_activate(client, db)
    r = client.post("/api/auth/forgot-password", json={"email": WHITELIST_EMAIL})
    assert r.status_code == 200
    row = (
        db.query(EmailToken)
        .join(Student, EmailToken.student_id == Student.id)
        .filter(Student.email == WHITELIST_EMAIL, EmailToken.purpose == "reset")
        .order_by(EmailToken.id.desc())
        .first()
    )
    r = client.post(
        "/api/auth/reset-password",
        json={"token": row.token, "new_password": "NewPassw0rd"},
    )
    assert r.status_code == 200
    r = client.post(
        "/api/auth/login", json={"email": WHITELIST_EMAIL, "password": "NewPassw0rd"}
    )
    assert r.status_code == 200
