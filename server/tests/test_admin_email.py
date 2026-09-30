"""邮件规则与运营接口用例（05 文档 3.2 #9、#10、#11）。"""
from datetime import timedelta

from app.models import EmailLog, LessonCard
from app.services.email_service import send_email
from app.timeutil import now_utc
from tests.conftest import (
    add_whitelist,
    register_and_activate,
    schedule_lesson,
    staff_login,
)


# #9 防重：24h 内同类型同学时再发 preview_reminder → 返回 skipped，不重复发
def test_dedup_24h_same_student_type_lesson(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "T01", at)
    from app.models import Student

    student = db.query(Student).filter_by(id=student_id).one()
    lesson = db.query(LessonCard).filter_by(code="T01").one()

    first = send_email(db, student, "preview_reminder", lesson, retry_delay=0)
    assert first == "sent"
    second = send_email(db, student, "preview_reminder", lesson, retry_delay=0)
    assert second == "skipped"
    sent = (
        db.query(EmailLog)
        .filter_by(student_id=student_id, mail_type="preview_reminder")
        .count()
    )
    assert sent == 1


# #10 排期时间跨天变更 → 触发 schedule_change 而非 schedule_confirm
def test_schedule_change_email_on_cross_day_update(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created = schedule_lesson(client, db, student_id, "T01", at)
    assert created["email_triggered"] == "schedule_confirm"

    next_day = (now_utc() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    staff = staff_login(client)
    r = client.put(
        f"/api/admin/schedules/{created['id']}",
        headers={"Authorization": f"Bearer {staff}"},
        json={"scheduled_at": next_day, "status": "scheduled"},
    )
    assert r.status_code == 200
    assert r.json()["email_triggered"] == "schedule_change"

    types = [
        row.mail_type
        for row in db.query(EmailLog).filter_by(student_id=student_id).order_by(EmailLog.id)
    ]
    assert types.count("schedule_confirm") == 1
    assert types.count("schedule_change") == 1


def test_schedule_same_day_update_no_email(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=4, hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created = schedule_lesson(client, db, student_id, "T01", at)

    same_day = (now_utc() + timedelta(days=4, hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    staff = staff_login(client)
    r = client.put(
        f"/api/admin/schedules/{created['id']}",
        headers={"Authorization": f"Bearer {staff}"},
        json={"scheduled_at": same_day, "status": "scheduled"},
    )
    assert r.status_code == 200
    assert r.json()["email_triggered"] is None


# #11 meeting_link 为空时发预习邮件 → 400 LINK_REQUIRED
def test_send_preview_reminder_requires_link(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created = schedule_lesson(client, db, student_id, "T01", at, meeting_link="")

    staff = staff_login(client)
    r = client.post(
        f"/api/admin/schedules/{created['id']}/send-reminder",
        headers={"Authorization": f"Bearer {staff}"},
        json={"mail_type": "preview_reminder"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "LINK_REQUIRED"


def test_admin_login_bootstrap_must_change_password(client):
    r = client.post(
        "/api/admin/login",
        json={"email": "admin@example.com", "password": "ChangeMe123!"},
    )
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True


def test_admin_change_password_flow(client):
    token = staff_login(client)
    r = client.post(
        "/api/admin/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "ChangeMe123!", "new_password": "NewStaffPass1"},
    )
    assert r.status_code == 200
    r = client.post(
        "/api/admin/login",
        json={"email": "admin@example.com", "password": "NewStaffPass1"},
    )
    assert r.status_code == 200
    assert r.json()["must_change_password"] is False


def test_admin_students_list_with_progress(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "C01", at)

    staff = staff_login(client)
    r = client.get("/api/admin/students", headers={"Authorization": f"Bearer {staff}"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["email_masked"].endswith("@example.com")
    assert item["progress"]["one_on_one_done"] == 0
    assert item["progress"]["preview_read_rate"] == 0.0


def test_admin_import_whitelist(client, db):
    staff = staff_login(client)
    r = client.post(
        "/api/admin/students",
        headers={"Authorization": f"Bearer {staff}"},
        json={"emails": ["a@example.com", "b@example.com"], "cohort_id": 1},
    )
    assert r.status_code == 200
    assert r.json() == {"imported": 2, "duplicated": 0}
    r = client.post(
        "/api/admin/students",
        headers={"Authorization": f"Bearer {staff}"},
        json={"emails": ["a@example.com", "c@example.com"], "cohort_id": 1},
    )
    assert r.json() == {"imported": 1, "duplicated": 1}


def test_admin_email_logs_and_retry(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "T01", at)

    staff = staff_login(client)
    r = client.get(
        "/api/admin/email-logs", headers={"Authorization": f"Bearer {staff}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    log = body["items"][0]
    assert log["to_email_masked"].endswith("@example.com")
    assert log["status"] == "sent"


def test_admin_send_welcome(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    staff = staff_login(client)
    r = client.post(
        f"/api/admin/students/{student_id}/send-welcome",
        headers={"Authorization": f"Bearer {staff}"},
    )
    assert r.status_code == 200
    assert db.query(EmailLog).filter_by(mail_type="welcome").count() == 1


def test_admin_preview_student_view(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "T01", at)

    staff = staff_login(client)
    r = client.get(
        "/api/admin/preview/student-view",
        params={"student_id": student_id},
        headers={"Authorization": f"Bearer {staff}"},
    )
    assert r.status_code == 200
    m2 = r.json()["modules"][1]
    assert m2["lessons"][0]["code"] == "T01"
    assert m2["lessons"][0]["display_status"] == "preview"


def test_calendar_ics(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created = schedule_lesson(client, db, student_id, "T01", at)
    r = client.get(f"/api/schedules/{created['id']}/calendar.ics")
    assert r.status_code == 200
    assert "BEGIN:VCALENDAR" in r.text
    assert "T01" in r.text
