"""E2E 全链路（05 文档 3.2 #18）：
注册 → 激活 → 排期 → T-2 → magic_link 直达（console 后端），
verify / schedule_confirm / preview_reminder / class_reminder 四类邮件按序产生。
"""
from datetime import timedelta

from app.models import EmailLog, EmailToken, Student
from app.services.scheduler import run_t0_reminders, run_t2_reminders
from app.timeutil import now_utc
from tests.conftest import WHITELIST_EMAIL, add_whitelist, register_and_activate, schedule_lesson, staff_login


def test_full_chain_e2e(client, db):
    add_whitelist(db)
    now = now_utc()

    # 1. 注册 → verify 邮件
    token, student_id = register_and_activate(client, db)
    assert db.query(EmailLog).filter_by(mail_type="verify").count() == 1
    student = db.query(Student).filter_by(id=student_id).one()
    assert student.status == "active"

    # 2. 排期（今+2.5 天，落 T-2 窗口）→ schedule_confirm
    at = (now + timedelta(days=2, hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created = schedule_lesson(client, db, student_id, "T01", at)
    assert created["email_triggered"] == "schedule_confirm"
    assert db.query(EmailLog).filter_by(mail_type="schedule_confirm").count() == 1

    # 3. 再排一节今天晚些的课 → confirm；T-0 任务触发 class_reminder
    today_at = (now + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "C01", today_at)
    assert db.query(EmailLog).filter_by(mail_type="schedule_confirm").count() == 2
    assert run_t0_reminders(db, now=now) == ["sent"]

    # 4. T-2 任务触发 preview_reminder（防重保证一封）
    assert run_t2_reminders(db, now=now) == ["sent"]
    assert run_t2_reminders(db, now=now) == ["skipped"]  # 24h 防重 → 不再发
    assert db.query(EmailLog).filter_by(mail_type="preview_reminder").count() == 1

    # 5. 邮件类型按序断言（四类）
    logs = db.query(EmailLog).order_by(EmailLog.id).all()
    assert [log.mail_type for log in logs] == [
        "verify",
        "schedule_confirm",
        "schedule_confirm",
        "class_reminder",
        "preview_reminder",
    ]
    assert all(log.status == "sent" for log in logs)

    # 6. magic_link 免登录直达：取最近生成的 magic token 换 JWT
    magic = (
        db.query(EmailToken)
        .filter_by(student_id=student_id, purpose="magic_link")
        .order_by(EmailToken.id.desc())
        .first()
    )
    assert magic is not None
    r = client.get(f"/api/links/magic/{magic.token}")
    assert r.status_code == 200
    magic_jwt = r.json()["token"]
    assert r.json()["student"]["email"] == WHITELIST_EMAIL

    # 7. 换到的 JWT 能直接访问学员接口（免登录）
    r = client.get("/api/map", headers={"Authorization": f"Bearer {magic_jwt}"})
    assert r.status_code == 200
    m2 = r.json()["modules"][1]
    assert m2["lessons"][0]["code"] == "T01"
    # T01 在今+2.5 天：T-2 解锁点（scheduled_at-2d）尚未到 → ready 而非 preview
    assert m2["lessons"][0]["display_status"] == "ready"

    # 8. magic token 一次性：再用 → TOKEN_INVALID
    r = client.get(f"/api/links/magic/{magic.token}")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "TOKEN_INVALID"


def test_admin_can_see_student_progress_after_chain(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "C01", at)

    staff = staff_login(client)
    r = client.get(
        "/api/admin/students",
        params={"stale": 1},
        headers={"Authorization": f"Bearer {staff}"},
    )
    assert r.status_code == 200
    # 刚登录的学员不算掉队
    assert all(item["id"] != student_id for item in r.json()["items"]) or r.json()["total"] == 0
