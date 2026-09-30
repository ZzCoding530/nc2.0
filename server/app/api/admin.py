"""运营后台接口（03 文档 §4）：staff token 专用，学员 token 一律 403 FORBIDDEN。"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.services import course_service as logic
from app.services import email_service as mail
from app.config import get_settings
from app.deps import get_current_staff, get_db, hash_password, verify_password
from app.errors import AppError
from app.models import Cohort, EmailLog, LessonCard, Schedule, StaffUser, Student, Whitelist
from app.schemas import (
    AdminChangePasswordIn,
    AdminLoginIn,
    ImportWhitelistIn,
    ScheduleUpdateIn,
    ScheduleUpsertIn,
    SendReminderIn,
)
from app.timeutil import in_shanghai, now_utc, parse_iso, to_iso

public_router = APIRouter(prefix="/admin", tags=["admin"])
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_staff)])


@public_router.post("/login")
def admin_login(payload: AdminLoginIn, db: Session = Depends(get_db)):
    staff = db.execute(
        select(StaffUser).where(StaffUser.email == payload.email.lower())
    ).scalar_one_or_none()
    if staff is None or not verify_password(payload.password, staff.password_hash):
        raise AppError("INVALID_CREDENTIALS")

    settings = get_settings()
    must_change = (
        payload.email.lower() == settings.admin_bootstrap_email.lower()
        and payload.password == settings.admin_bootstrap_password
    )
    return {"token": _staff_jwt(staff), "staff": {"name": staff.name}, "must_change_password": must_change}


def _staff_jwt(staff: StaffUser) -> str:
    from app.deps import create_jwt

    return create_jwt(staff.id, "staff")


@router.post("/change-password")
def change_password(
    payload: AdminChangePasswordIn,
    staff: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, staff.password_hash):
        raise AppError("INVALID_CREDENTIALS")
    staff.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}


@router.get("/cohorts")
def list_cohorts(db: Session = Depends(get_db)):
    items = db.execute(select(Cohort).order_by(Cohort.id)).scalars().all()
    return {"items": [{"id": c.id, "name": c.name, "status": c.status} for c in items]}


@router.get("/lesson-cards")
def list_lesson_cards(db: Session = Depends(get_db)):
    from app.models import Module

    rows = db.execute(
        select(LessonCard, Module.code).join(Module, LessonCard.module_id == Module.id).order_by(LessonCard.sort_order)
    ).all()
    return {
        "items": [
            {
                "id": lesson.id,
                "code": lesson.code,
                "title": lesson.title,
                "lesson_type": lesson.lesson_type,
                "module_code": module_code,
                "part_group": lesson.part_group,
            }
            for lesson, module_code in rows
        ]
    }


@router.get("/students")
def list_students(
    cohort_id: int | None = None,
    stale: int = 0,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    from datetime import timedelta

    now = now_utc()
    query = select(Student).order_by(Student.id)
    if cohort_id:
        query = query.where(Student.cohort_id == cohort_id)
    if stale:
        threshold = now - timedelta(days=7)
        query = query.where((Student.last_login_at.is_(None) & (Student.created_at < threshold)) | (Student.last_login_at < threshold))
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar()
    items = db.execute(query.limit(page_size).offset((page - 1) * page_size)).scalars().all()
    return {
        "items": [
            {
                "id": s.id,
                "name": s.name,
                "email_masked": logic.mask_email(s.email),
                "cohort_id": s.cohort_id,
                "cohort": s.cohort.name,
                "status": s.status,
                "progress": {
                    "one_on_one_done": logic.progress_counts(db, s.id)["one_on_one"]["done"],
                    "preview_read_rate": logic.preview_read_rate(db, s.id, now),
                    "recorded_done": logic.progress_counts(db, s.id)["recorded"]["done"],
                },
                "last_login_at": to_iso(s.last_login_at),
            }
            for s in items
        ],
        "total": total,
    }


@router.post("/students")
def import_whitelist(payload: ImportWhitelistIn, db: Session = Depends(get_db)):
    if db.get(Cohort, payload.cohort_id) is None:
        raise AppError("NOT_FOUND", "班期不存在")
    imported = duplicated = 0
    for raw in payload.emails:
        email = raw.lower()
        exists = db.execute(select(Whitelist.id).where(Whitelist.email == email)).first()
        if exists:
            duplicated += 1
            continue
        db.add(Whitelist(email=email, cohort_id=payload.cohort_id))
        imported += 1
    db.commit()
    return {"imported": imported, "duplicated": duplicated}


@router.post("/students/{student_id}/send-welcome")
def send_welcome(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise AppError("NOT_FOUND")
    result = mail.send_email(db, student, "welcome", None, retry_delay=0)
    return {"ok": True, "result": result}


@router.get("/schedules")
def list_schedules(
    cohort_id: int | None = None,
    student_id: int | None = None,
    lesson_code: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(Schedule).order_by(Schedule.id)
    if cohort_id:
        query = query.where(Schedule.student_id.in_(select(Student.id).where(Student.cohort_id == cohort_id)))
    if student_id:
        query = query.where(Schedule.student_id == student_id)
    if lesson_code:
        query = query.where(
            Schedule.lesson_card_id.in_(select(LessonCard.id).where(LessonCard.code == lesson_code))
        )
    rows = db.execute(query).scalars().all()
    return {
        "items": [
            {
                "id": s.id,
                "student_id": s.student_id,
                "lesson_card_id": s.lesson_card_id,
                "lesson_code": s.lesson_card.code,
                "scheduled_at": to_iso(s.scheduled_at),
                "meeting_link": s.meeting_link,
                "status": s.status,
                "updated_at": to_iso(s.updated_at),
            }
            for s in rows
        ]
    }


def _parse_scheduled_at(value: str | None):
    if value in (None, ""):
        return None
    try:
        return parse_iso(value)
    except ValueError:
        raise AppError("VALIDATION_ERROR", "时间格式需为 UTC ISO8601，如 2026-10-10T12:00:00Z")


def _apply_and_notify(db: Session, schedule: Schedule, old_at, old_status, new_at, new_status, new_link) -> str | None:
    """保存排期并触发邮件（03 文档 §4）：
    首次排期 → schedule_confirm；时间跨天变更 → schedule_change（原→新）。
    """
    schedule.scheduled_at = new_at
    if new_status is not None:
        schedule.status = new_status
    if new_link is not None:
        schedule.meeting_link = new_link
    schedule.updated_at = now_utc()
    db.commit()

    triggered = None
    student = schedule.student
    lesson = schedule.lesson_card
    if new_status == "scheduled" and new_at is not None:
        if old_at is None or old_status == "planned":
            triggered = "schedule_confirm"
            mail.send_email(db, student, "schedule_confirm", lesson, retry_delay=0)
        elif in_shanghai(old_at).date() != in_shanghai(new_at).date():
            triggered = "schedule_change"
            mail.send_schedule_change(db, student, lesson, old_at, new_at, schedule)
    return triggered


@router.post("/schedules")
def upsert_schedule(payload: ScheduleUpsertIn, db: Session = Depends(get_db)):
    student = db.get(Student, payload.student_id)
    if student is None:
        raise AppError("NOT_FOUND", "学员不存在")
    if payload.lesson_card_id:
        lesson = db.get(LessonCard, payload.lesson_card_id)
    elif payload.lesson_code:
        lesson = db.execute(
            select(LessonCard).where(LessonCard.code == payload.lesson_code)
        ).scalar_one_or_none()
    else:
        raise AppError("VALIDATION_ERROR", "需提供 lesson_card_id 或 lesson_code")
    if lesson is None:
        raise AppError("NOT_FOUND", "课时不存在")

    schedule = db.execute(
        select(Schedule).where(
            Schedule.student_id == student.id, Schedule.lesson_card_id == lesson.id
        )
    ).scalar_one_or_none()
    old_at = schedule.scheduled_at if schedule else None
    old_status = schedule.status if schedule else "planned"
    if schedule is None:
        schedule = Schedule(student_id=student.id, lesson_card_id=lesson.id)
        db.add(schedule)
        db.flush()

    triggered = _apply_and_notify(
        db,
        schedule,
        old_at,
        old_status,
        _parse_scheduled_at(payload.scheduled_at),
        payload.status,
        payload.meeting_link,
    )
    return {"ok": True, "id": schedule.id, "email_triggered": triggered}


@router.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: int, payload: ScheduleUpdateIn, db: Session = Depends(get_db)):
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise AppError("NOT_FOUND")

    old_at = schedule.scheduled_at
    old_status = schedule.status
    new_at = _parse_scheduled_at(payload.scheduled_at) if payload.scheduled_at is not None else old_at
    new_status = payload.status or schedule.status
    new_link = payload.meeting_link if payload.meeting_link is not None else schedule.meeting_link

    triggered = _apply_and_notify(db, schedule, old_at, old_status, new_at, new_status, new_link)
    return {"ok": True, "email_triggered": triggered}


@router.post("/schedules/{schedule_id}/send-reminder")
def send_reminder(schedule_id: int, payload: SendReminderIn, db: Session = Depends(get_db)):
    if payload.mail_type not in ("preview_reminder", "class_reminder"):
        raise AppError("VALIDATION_ERROR", "mail_type 仅支持 preview_reminder / class_reminder")
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise AppError("NOT_FOUND")
    if not schedule.meeting_link:
        raise AppError("LINK_REQUIRED")

    result = mail.send_email(db, schedule.student, payload.mail_type, schedule.lesson_card, retry_delay=0)
    return {"ok": True, "queued": result == "sent", "result": result}


@router.get("/email-logs")
def list_email_logs(
    mail_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    query = select(EmailLog).order_by(EmailLog.id.desc())
    if mail_type:
        query = query.where(EmailLog.mail_type == mail_type)
    if status:
        query = query.where(EmailLog.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar()
    items = db.execute(query.limit(page_size).offset((page - 1) * page_size)).scalars().all()
    lesson_codes = {
        lesson.id: lesson.code
        for lesson in db.execute(select(LessonCard).where(LessonCard.id.in_(
            [log.lesson_card_id for log in items if log.lesson_card_id]
        ))).scalars()
    }
    return {
        "items": [
            {
                "id": log.id,
                "to_email_masked": logic.mask_email(log.to_email),
                "mail_type": log.mail_type,
                "lesson_code": lesson_codes.get(log.lesson_card_id),
                "status": log.status,
                "retry_count": log.retry_count,
                "sent_at": to_iso(log.sent_at),
                "created_at": to_iso(log.created_at),
                "error_msg": log.error_msg,
            }
            for log in items
        ],
        "total": total,
    }


@router.post("/email-logs/{log_id}/retry")
def retry_email(log_id: int, db: Session = Depends(get_db)):
    log = db.get(EmailLog, log_id)
    if log is None:
        raise AppError("NOT_FOUND")
    if log.status != "failed":
        raise AppError("VALIDATION_ERROR", "仅失败邮件可重发")
    result = mail.retry_email_log(db, log, retry_delay=0)
    return {"ok": result == "sent", "result": result}


@router.get("/preview/student-view")
def preview_student_view(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise AppError("NOT_FOUND")
    return logic.build_map_payload(db, student.id)
