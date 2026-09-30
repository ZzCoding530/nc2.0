"""定时任务用例（05 文档 3.2 #16、#17）：任务体为纯函数，直接传 now，禁止 sleep。"""
from datetime import timedelta

from app.models import LessonCard, Schedule
from app.services.scheduler import run_auto_close, run_failed_retry, run_t0_reminders, run_t2_reminders
from app.timeutil import now_utc
from tests.conftest import add_whitelist, register_and_activate


def _make_schedule(db, student_id, code, scheduled_at, status="scheduled"):
    lesson = db.query(LessonCard).filter_by(code=code).one()
    row = Schedule(
        student_id=student_id,
        lesson_card_id=lesson.id,
        scheduled_at=scheduled_at,
        meeting_link="https://meeting.example.com/x",
        status=status,
    )
    db.add(row)
    db.commit()
    return row


# #16 T-2 定时任务：scheduled_at 落窗口 [今+2, 今+3) → 命中且不漏不错发
def test_t2_window_hits_exactly(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    now = now_utc()

    hit = _make_schedule(db, student_id, "T01", now + timedelta(days=2, hours=12))  # 窗口内
    miss_early = _make_schedule(db, student_id, "T02", now + timedelta(days=1, hours=12))  # [今+1,今+2)
    miss_late = _make_schedule(db, student_id, "T03", now + timedelta(days=3, hours=12))  # >= 今+3
    miss_planned = _make_schedule(db, student_id, "C01", now + timedelta(days=2, hours=12), status="planned")

    results = run_t2_reminders(db, now=now)
    assert results == ["sent"]

    from app.models import EmailLog

    logs = db.query(EmailLog).filter_by(mail_type="preview_reminder").all()
    assert len(logs) == 1
    assert logs[0].lesson_card_id == hit.lesson_card_id
    for row in (miss_early, miss_late, miss_planned):
        assert row.status in ("scheduled", "planned")


def test_t2_window_shanghai_day_bounds(db, client):
    """窗口边界按上海日历日：[今+2 00:00, 今+3 00:00) 上海时间。"""
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    from app.timeutil import sh_date_bounds

    now = now_utc()
    start, end = sh_date_bounds(now, day_offset=2)
    assert start < end
    _make_schedule(db, student_id, "T01", start)  # 下界含
    _make_schedule(db, student_id, "T02", end - timedelta(seconds=1))  # 上界不含前
    _make_schedule(db, student_id, "T03", end)  # 上界不含

    results = run_t2_reminders(db, now=now)
    assert results.count("sent") == 2


def test_t0_reminders_today_only(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    now = now_utc()
    _make_schedule(db, student_id, "T01", now + timedelta(hours=3))  # 今天
    _make_schedule(db, student_id, "T02", now + timedelta(days=1, hours=3))  # 明天

    results = run_t0_reminders(db, now=now)
    assert results == ["sent"]
    from app.models import EmailLog

    assert db.query(EmailLog).filter_by(mail_type="class_reminder").count() == 1


# #17 自动结课：过 24h 兜底 done
def test_auto_close_after_24h(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    now = now_utc()
    stale = _make_schedule(db, student_id, "T01", now - timedelta(hours=25))
    fresh = _make_schedule(db, student_id, "T02", now - timedelta(hours=23))

    closed = run_auto_close(db, now=now)
    assert closed == 1
    assert stale.status == "done"
    assert fresh.status == "scheduled"


def test_failed_retry_resends(client, db):
    add_whitelist(db)
    _, student_id = register_and_activate(client, db)
    from app.models import EmailLog, Student

    student = db.query(Student).filter_by(id=student_id).one()
    log = EmailLog(
        student_id=student.id,
        to_email=student.email,
        mail_type="welcome",
        subject="欢迎加入 NiceOffer 202610 期",
        body="三步开始学习……",
        status="failed",
        retry_count=0,
        error_msg="smtp down",
    )
    db.add(log)
    db.commit()

    results = run_failed_retry(db, now=now_utc())
    assert results == ["sent"]
    assert log.status == "sent"
    assert log.retry_count == 0  # 成功路径不再累计 retry_count

    log.status = "failed"
    log.retry_count = 2  # 达上限 → 不再重试
    db.commit()
    results = run_failed_retry(db, now=now_utc())
    assert results == []
