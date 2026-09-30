"""定时任务（04 文档 §6.8，05 文档 §3.3）。

纪律：任务体是可直接调用的纯函数（传入 now），测试不依赖 cron；
cron 壳（APScheduler 注册）本身不测。
"""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.timeutil import now_utc, sh_date_bounds
from app.services import email_service


def _schedules_between(db: Session, start, end):
    from app.models import Schedule

    return db.execute(
        select(Schedule).where(
            Schedule.status == "scheduled",
            Schedule.scheduled_at >= start,
            Schedule.scheduled_at < end,
        )
    ).scalars().all()


def run_t2_reminders(db: Session, now=None) -> list[str]:
    """T-2 预习提醒：scheduled_at 落 [今+2天, 今+3天)（上海日历日窗口）。"""
    now = now or now_utc()
    start, end = sh_date_bounds(now, day_offset=2)
    results = []
    for schedule in _schedules_between(db, start, end):
        if not schedule.meeting_link:
            continue  # 定时任务遇空链接跳过（手动发送才报 LINK_REQUIRED）
        results.append(
            email_service.send_email(
                db, schedule.student, "preview_reminder", schedule.lesson_card,
                now=now, retry_delay=0,
            )
        )
    return results


def run_t0_reminders(db: Session, now=None) -> list[str]:
    """T-0 上课提醒：scheduled_at 在今天（上海日历日）。"""
    now = now or now_utc()
    start, end = sh_date_bounds(now, day_offset=0)
    results = []
    for schedule in _schedules_between(db, start, end):
        if not schedule.meeting_link:
            continue
        results.append(
            email_service.send_email(
                db, schedule.student, "class_reminder", schedule.lesson_card,
                now=now, retry_delay=0,
            )
        )
    return results


def run_failed_retry(db: Session, now=None) -> list[str]:
    """失败重发：status=failed 且 retry_count<2。"""
    from app.models import EmailLog

    now = now or now_utc()
    logs = db.execute(
        select(EmailLog).where(EmailLog.status == "failed", EmailLog.retry_count < 2)
    ).scalars().all()
    return [email_service.retry_email_log(db, log, now=now, retry_delay=0) for log in logs]


def run_auto_close(db: Session, now=None) -> int:
    """自动结课兜底：scheduled_at 已过 24h 且仍 scheduled → done。"""
    from app.models import Schedule

    now = now or now_utc()
    stale = db.execute(
        select(Schedule).where(
            Schedule.status == "scheduled",
            Schedule.scheduled_at < now - timedelta(hours=24),
        )
    ).scalars().all()
    for schedule in stale:
        schedule.status = "done"
    db.commit()
    return len(stale)


def register_scheduler(get_db_session) -> None:  # pragma: no cover - cron 壳不测
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler()

    def _job(fn):
        db = get_db_session()
        try:
            fn(db)
        finally:
            db.close()

    scheduler.add_job(lambda: _job(run_t2_reminders), CronTrigger(hour=10, minute=0, timezone="Asia/Shanghai"))
    scheduler.add_job(lambda: _job(run_t0_reminders), CronTrigger(hour=9, minute=0, timezone="Asia/Shanghai"))
    scheduler.add_job(lambda: _job(run_failed_retry), CronTrigger(minute=0))
    scheduler.add_job(lambda: _job(run_auto_close), CronTrigger(hour=23, minute=59, timezone="Asia/Shanghai"))
    scheduler.start()
