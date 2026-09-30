"""学员端课程数据接口（03 文档 §3）：只读 + 轻标记 + magic link 落地。"""
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services import email_service as mail
from app.services import course_service as logic
from app.deps import create_jwt, get_current_student, get_db
from app.errors import AppError
from app.models import Activity, LessonCard, Schedule, Student
from app.schemas import ActivityIn
from app.timeutil import now_utc, preview_unlocked, to_iso, to_naive_utc

router = APIRouter(tags=["student"])


@router.get("/me")
def me(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "email": student.email,
            "cohort": student.cohort.name,
        },
        "links": {
            "brush_sop_url": mail.get_config(db, "brush_sop_url", ""),
            "qa_contact": mail.get_config(db, "qa_contact", ""),
            "ds_checklist_url": mail.get_config(db, "ds_checklist_url", ""),
        },
    }


@router.get("/overview")
def overview(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    return logic.build_overview_payload(db, student)


@router.get("/map")
def course_map(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    return logic.build_map_payload(db, student.id)


@router.get("/lessons/{code}")
def lesson_detail(code: str, student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    lesson = db.execute(select(LessonCard).where(LessonCard.code == code)).scalar_one_or_none()
    if lesson is None:
        raise AppError("NOT_FOUND")

    schedule = db.execute(
        select(Schedule).where(
            Schedule.student_id == student.id, Schedule.lesson_card_id == lesson.id
        )
    ).scalar_one_or_none()

    now = now_utc()
    unlocked = bool(
        schedule
        and schedule.status == "scheduled"
        and schedule.scheduled_at is not None
        and preview_unlocked(schedule.scheduled_at, now)
    )
    preview_read = logic.has_activity(db, student.id, lesson.id, "preview_read")

    preview_payload = None
    if unlocked and lesson.lesson_type in logic.ONE_ON_ONE_TYPES:
        data = logic.load_preview_json(lesson)
        if data:
            preview_payload = {
                "intro": data.get("intro", ""),
                "questions": data.get("questions", []),
                "keywords": data.get("keywords", []),
            }

    recorded_items = None
    code_url = None
    if lesson.lesson_type == "recorded":
        acts = logic.activity_set(db, student.id)
        siblings = (
            db.execute(
                select(LessonCard)
                .where(LessonCard.part_group == lesson.part_group)
                .order_by(LessonCard.sort_order)
            ).scalars().all()
            if lesson.part_group
            else [lesson]
        )
        recorded_items = [
            {
                "code": item.code,
                "title": item.title,
                "duration_min": item.duration_min,
                "video_url": item.video_url,
                "done": (item.id, "recorded_done") in acts,
            }
            for item in siblings
        ]
        code_url = mail.get_config(db, "code_package_url", "")

    return {
        "code": lesson.code,
        "title": lesson.title,
        "type": lesson.lesson_type,
        "module_title": lesson.module.title,
        "duration_min": lesson.duration_min,
        "effort_note": lesson.effort_note,
        "content_summary": lesson.content_summary,
        "schedule": (
            {
                "scheduled_at": to_iso(schedule.scheduled_at),
                "meeting_link": schedule.meeting_link,
                "status": schedule.status,
            }
            if schedule
            else None
        ),
        "preview_unlocked": unlocked,
        "preview": preview_payload,  # 未到 T-2 返回 null（后端拦截，防越权）
        "preview_read": preview_read,
        "materials": [
            {
                "id": m.id,
                "title": m.title,
                "mat_type": m.mat_type,
                "required": bool(m.required),
                "url": m.url,
            }
            for m in lesson.materials
        ],
        "homework_def": lesson.homework_def,
        "homework_note": "V1 作业通过邮件提交，讲师在下次 1v1 面评中点评",
        "recorded_items": recorded_items,
        "code_url": code_url,
    }


@router.post("/lessons/{code}/activity")
def mark_activity(
    code: str,
    payload: ActivityIn,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    if payload.act_type not in ("preview_read", "recorded_done"):
        raise AppError("VALIDATION_ERROR", "act_type 仅支持 preview_read / recorded_done")

    lesson = db.execute(select(LessonCard).where(LessonCard.code == code)).scalar_one_or_none()
    if lesson is None:
        raise AppError("NOT_FOUND")

    if payload.act_type == "preview_read":
        schedule = db.execute(
            select(Schedule).where(
                Schedule.student_id == student.id, Schedule.lesson_card_id == lesson.id
            )
        ).scalar_one_or_none()
        if schedule is None or schedule.status != "scheduled" or schedule.scheduled_at is None:
            raise AppError("FORBIDDEN", "仅可标记自己排期内的课时")
        if not preview_unlocked(schedule.scheduled_at, now_utc()):
            raise AppError("LESSON_LOCKED")
    else:
        if lesson.lesson_type != "recorded":
            raise AppError("VALIDATION_ERROR", "recorded_done 仅适用于录播课时")

    exists = db.execute(
        select(Activity.id).where(
            Activity.student_id == student.id,
            Activity.lesson_card_id == lesson.id,
            Activity.act_type == payload.act_type,
        )
    ).first()
    if exists is None:  # 幂等：UNIQUE + upsert
        db.add(
            Activity(
                student_id=student.id,
                lesson_card_id=lesson.id,
                act_type=payload.act_type,
            )
        )
        db.commit()
    return {"ok": True}


@router.get("/links/magic/{token}")
def magic_link_landing(token: str, db: Session = Depends(get_db)):
    """邮件直达落地（03 文档 §3.6）：token 换 JWT（7 天有效期内一次性）。"""
    from app.api.auth import _consume_token

    now = now_utc()
    record = _consume_token(db, token, "magic_link", now)
    student = db.get(Student, record.student_id)
    db.commit()
    return {
        "token": create_jwt(student.id, "student", days=14),
        "student": {"id": student.id, "name": student.name, "email": student.email},
    }


@router.get("/schedules/{schedule_id}/calendar.ics")
def calendar_ics(schedule_id: int, db: Session = Depends(get_db)):
    """邮件内「加入日历」链接（04 文档 §6.4 的 ics_link）。"""
    from datetime import timedelta

    schedule = db.get(Schedule, schedule_id)
    if schedule is None or schedule.scheduled_at is None:
        raise AppError("NOT_FOUND")

    start = to_naive_utc(schedule.scheduled_at)
    end = start + timedelta(minutes=schedule.lesson_card.duration_min or 60)
    lesson = schedule.lesson_card
    ics = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//NiceOffer//Schedule//CN",
            "BEGIN:VEVENT",
            f"UID:niceoffer-schedule-{schedule.id}@niceoffer",
            f"SUMMARY:{lesson.code} {lesson.title}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
            f"LOCATION:{schedule.meeting_link}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    return Response(
        content=ics,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{lesson.code}.ics"'},
    )
