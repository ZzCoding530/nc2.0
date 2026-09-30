"""学员课程接口用例（05 文档 3.2 #7、#8、#14、#15）。"""
from datetime import timedelta

from app.models import LessonCard, Schedule
from app.services.course_service import derive_display_status, progress_counts
from app.timeutil import now_utc
from tests.conftest import add_whitelist, register_and_activate, schedule_lesson


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# #7 T-2 前请求课时详情 → preview=null 且 preview_unlocked=false（后端拦截）
def test_lesson_detail_preview_locked_before_t2(client, db):
    add_whitelist(db)
    token, student_id = register_and_activate(client, db)
    future = (now_utc() + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "T01", future)

    r = client.get("/api/lessons/T01", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["preview"] is None
    assert body["preview_unlocked"] is False


def test_lesson_detail_preview_unlocked_at_t2(client, db):
    add_whitelist(db)
    token, student_id = register_and_activate(client, db)
    soon = (now_utc() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")  # T-2 已过
    schedule_lesson(client, db, student_id, "T01", soon)

    r = client.get("/api/lessons/T01", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["preview_unlocked"] is True
    assert body["preview"] is not None
    assert len(body["preview"]["questions"]) == 3


def test_lesson_detail_not_found(client, db):
    add_whitelist(db)
    token, _ = register_and_activate(client, db)
    r = client.get("/api/lessons/NOPE", headers=_auth(token))
    assert r.status_code == 404


# #8 同一 activity 重复标记 → 200 幂等，数据库只有一行
def test_activity_mark_idempotent(client, db):
    from app.models import Activity

    add_whitelist(db)
    token, student_id = register_and_activate(client, db)
    soon = (now_utc() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "C01", soon)

    for _ in range(2):
        r = client.post(
            "/api/lessons/C01/activity", json={"act_type": "preview_read"}, headers=_auth(token)
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
    rows = (
        db.query(Activity)
        .join(LessonCard, Activity.lesson_card_id == LessonCard.id)
        .filter(LessonCard.code == "C01")
        .all()
    )
    assert len(rows) == 1


def test_activity_preview_before_t2_rejected(client, db):
    add_whitelist(db)
    token, student_id = register_and_activate(client, db)
    future = (now_utc() + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "C01", future)
    r = client.post(
        "/api/lessons/C01/activity", json={"act_type": "preview_read"}, headers=_auth(token)
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "LESSON_LOCKED"


def test_activity_recorded_done(client, db):
    add_whitelist(db)
    token, _ = register_and_activate(client, db)
    r = client.post(
        "/api/lessons/D01/activity", json={"act_type": "recorded_done"}, headers=_auth(token)
    )
    assert r.status_code == 200
    r = client.get("/api/lessons/D01", headers=_auth(token))
    assert r.json()["recorded_items"] is not None
    assert r.json()["recorded_items"][0]["done"] is True


# #14 display_status 五态推导（02 文档 §4 口径表逐条一致）
def test_display_status_five_states(db):
    lesson = db.query(LessonCard).filter_by(code="T01").one()
    recorded = db.query(LessonCard).filter_by(code="D01").one()
    now = now_utc()
    at = now + timedelta(days=3)

    s_done = Schedule(status="done")
    s_skipped = Schedule(status="skipped")
    s_scheduled = Schedule(status="scheduled", scheduled_at=at)
    s_scheduled_past = Schedule(status="scheduled", scheduled_at=now + timedelta(days=1))

    assert derive_display_status(lesson, s_done, False, now) == "done"
    assert derive_display_status(lesson, s_skipped, False, now) == "done"
    assert derive_display_status(lesson, None, False, now) == "pending"
    assert derive_display_status(lesson, Schedule(status="planned"), False, now) == "pending"
    # scheduled 且 T-2 已到 且无 preview_read → preview
    assert derive_display_status(lesson, s_scheduled_past, False, now) == "preview"
    # T-2 已到但已读 → ready；T-2 未到 → ready
    assert derive_display_status(lesson, s_scheduled_past, True, now) == "ready"
    assert derive_display_status(lesson, s_scheduled, False, now) == "ready"
    # locked：录播未开放（V1 全开放，part_open=False 预留）
    assert derive_display_status(recorded, None, False, now, part_open=False) == "locked"


# #15 进度口径：done=3 → 3/15（分子分母与 02 文档 §4 一致）
def test_progress_counts_3_of_15(client, db):
    add_whitelist(db)
    token, student_id = register_and_activate(client, db)
    at = (now_utc() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for code in ("C01", "C02", "T01"):
        schedule_lesson(client, db, student_id, code, at)
        schedule_row = (
            db.query(Schedule)
            .join(LessonCard, Schedule.lesson_card_id == LessonCard.id)
            .filter(Schedule.student_id == student_id, LessonCard.code == code)
            .one()
        )
        schedule_row.status = "done"
    db.commit()

    p = progress_counts(db, student_id)
    assert p == {"one_on_one": {"done": 3, "total": 15}, "recorded": {"done": 0, "total": 27}}

    r = client.get("/api/overview", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["progress"] == p


def test_overview_next_lesson_and_todo(client, db):
    add_whitelist(db)
    token, student_id = register_and_activate(client, db)
    soon = (now_utc() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "T01", soon)

    r = client.get("/api/overview", headers=_auth(token))
    body = r.json()
    assert body["next_lesson"]["code"] == "T01"
    assert body["next_lesson"]["status"] == "preview"
    todos = [t for t in body["todos"] if t["kind"] == "preview"]
    assert todos and todos[0]["lesson_code"] == "T01" and todos[0]["acted"] is False


def test_map_payload_structure(client, db):
    add_whitelist(db)
    token, student_id = register_and_activate(client, db)
    soon = (now_utc() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule_lesson(client, db, student_id, "T01", soon)

    r = client.get("/api/map", headers=_auth(token))
    assert r.status_code == 200
    modules = r.json()["modules"]
    assert [m["code"] for m in modules] == ["M1", "M2", "M3", "M4", "FLEX"]
    m2 = modules[1]
    assert m2["lessons"][0]["code"] == "T01"
    assert m2["lessons"][0]["display_status"] == "preview"
    assert m2["lessons"][0]["is_current"] is True
    m4_lessons = modules[3]["lessons"]
    assert len(m4_lessons) == 30  # D×27 + V×3
    assert all(les["display_status"] == "pending" for les in m4_lessons)


def test_me_links(client, db):
    add_whitelist(db)
    token, _ = register_and_activate(client, db)
    r = client.get("/api/me", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["student"]["email"]
    assert "qa_contact" in body["links"]
