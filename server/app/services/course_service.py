"""课程业务口径（02 文档 §4「关键查询口径」——与 PRD 对齐，勿各写各的）。"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Activity, LessonCard, Module, Schedule, Student
from app.timeutil import now_utc, preview_unlocked

ONE_ON_ONE_TYPES = ("1v1", "validation")


def load_preview_json(lesson: LessonCard) -> dict | None:
    if not lesson.preview:
        return None
    try:
        return json.loads(lesson.preview)
    except ValueError:
        return None


def derive_display_status(
    lesson: LessonCard,
    schedule: Schedule | None,
    preview_read: bool,
    now=None,
    part_open: bool = True,
    recorded_done: bool = False,
) -> str:
    """五态推导（02 文档 §4 / 03 文档 GET /map）：
    done←schedule.done（面授）/ recorded_done（录播）；preview←scheduled 且 T-2 已到
    且无 preview_read；ready←scheduled；pending←planned 未到解锁；
    locked←录播未开放（V1 全开放，part_open 预留 V1.5 分部分开放）。
    skipped（免修）视为 done 展示。
    """
    now = now or now_utc()
    if lesson.lesson_type == "recorded":
        if not part_open:
            return "locked"
        return "done" if recorded_done else "pending"
    if schedule is None or schedule.status == "planned":
        return "pending"
    if schedule.status in ("done", "skipped"):
        return "done"
    # status == 'scheduled'
    if (
        lesson.lesson_type in ONE_ON_ONE_TYPES
        and preview_unlocked(schedule.scheduled_at, now)
        and not preview_read
    ):
        return "preview"
    return "ready"


def progress_counts(db: Session, student_id: int) -> dict:
    """1v1 分母 15（1v1+validation），分子 schedule done；录播分母 27，分子 recorded_done。"""
    one_total = len(
        db.execute(
            select(LessonCard.id).where(LessonCard.lesson_type.in_(ONE_ON_ONE_TYPES))
        ).all()
    )
    one_done = len(
        db.execute(
            select(Schedule.id).where(
                Schedule.student_id == student_id,
                Schedule.status == "done",
                Schedule.lesson_card_id.in_(
                    select(LessonCard.id).where(LessonCard.lesson_type.in_(ONE_ON_ONE_TYPES))
                ),
            )
        ).all()
    )
    rec_total = len(
        db.execute(select(LessonCard.id).where(LessonCard.lesson_type == "recorded")).all()
    )
    rec_done = len(
        db.execute(
            select(Activity.id).where(
                Activity.student_id == student_id,
                Activity.act_type == "recorded_done",
                Activity.lesson_card_id.in_(
                    select(LessonCard.id).where(LessonCard.lesson_type == "recorded")
                ),
            )
        ).all()
    )
    return {
        "one_on_one": {"done": one_done, "total": one_total},
        "recorded": {"done": rec_done, "total": rec_total},
    }


def next_lesson(db: Session, student_id: int, now=None):
    """下一节课：status='scheduled' 且 scheduled_at > now，最早一条（02 文档 §4）。"""
    now = now or now_utc()
    return db.execute(
        select(Schedule)
        .where(
            Schedule.student_id == student_id,
            Schedule.status == "scheduled",
            Schedule.scheduled_at > now,
        )
        .order_by(Schedule.scheduled_at)
        .limit(1)
    ).scalar_one_or_none()


def activity_set(db: Session, student_id: int) -> set[tuple[int, str]]:
    rows = db.execute(
        select(Activity.lesson_card_id, Activity.act_type).where(Activity.student_id == student_id)
    ).all()
    return {(r[0], r[1]) for r in rows}


def has_activity(db: Session, student_id: int, lesson_card_id: int, act_type: str) -> bool:
    return (
        db.execute(
            select(Activity.id).where(
                Activity.student_id == student_id,
                Activity.lesson_card_id == lesson_card_id,
                Activity.act_type == act_type,
            )
        ).first()
        is not None
    )


def build_map_payload(db: Session, student_id: int, now=None) -> dict:
    """GET /map 与 GET /admin/preview/student-view 共用（03 文档 §3/§4）。"""
    now = now or now_utc()
    acts = activity_set(db, student_id)
    schedules = {
        s.lesson_card_id: s
        for s in db.execute(
            select(Schedule).where(Schedule.student_id == student_id)
        ).scalars()
    }
    nxt = next_lesson(db, student_id, now)
    current_card_id = nxt.lesson_card_id if nxt else None

    modules = db.execute(select(Module).order_by(Module.sort_order)).scalars().all()
    out_modules = []
    for m in modules:
        lessons = []
        for lesson in db.execute(
            select(LessonCard)
            .where(LessonCard.module_id == m.id)
            .order_by(LessonCard.sort_order)
        ).scalars():
            schedule = schedules.get(lesson.id)
            preview_read = (lesson.id, "preview_read") in acts
            recorded_done = (lesson.id, "recorded_done") in acts
            lessons.append(
                {
                    "code": lesson.code,
                    "title": lesson.title,
                    "type": lesson.lesson_type,
                    "display_status": derive_display_status(
                        lesson, schedule, preview_read, now,
                        recorded_done=recorded_done,
                    ),
                    "scheduled_at": _iso(schedule.scheduled_at if schedule else None),
                    "is_current": lesson.id == current_card_id,
                    "part_group": lesson.part_group,
                }
            )
        out_modules.append(
            {
                "code": m.code,
                "title": m.title,
                "subtitle": m.subtitle,
                "lessons": lessons,
            }
        )
    return {"modules": out_modules}


def build_overview_payload(db: Session, student: Student, now=None) -> dict:
    """GET /overview：进度 + 下一节课 + 待办（03 文档 §3.2）。"""
    now = now or now_utc()
    progress = progress_counts(db, student.id)
    nxt = next_lesson(db, student.id, now)

    next_lesson_payload = None
    todos = []

    if nxt:
        lesson = nxt.lesson_card
        read = has_activity(db, student.id, lesson.id, "preview_read")
        unlocked = preview_unlocked(nxt.scheduled_at, now)
        next_lesson_payload = {
            "code": lesson.code,
            "title": lesson.title,
            "scheduled_at": _iso(nxt.scheduled_at),
            "meeting_link": nxt.meeting_link,
            "status": "preview" if (unlocked and not read) else "ready",
            "preview_unlocked": unlocked,
        }
        if lesson.lesson_type in ONE_ON_ONE_TYPES and unlocked and not read:
            todos.append(
                {
                    "kind": "preview",
                    "lesson_code": lesson.code,
                    "title": "预习 · 三问预写",
                    "acted": False,
                }
            )
    else:
        next_lesson_payload = {
            "code": None,
            "title": None,
            "scheduled_at": None,
            "meeting_link": None,
            "status": None,
            "preview_unlocked": False,
        }

    # 录播待办：按 part_group 汇总（03 文档 todos 示例）
    acts = activity_set(db, student.id)
    groups: dict[str, dict] = {}
    for lesson in db.execute(
        select(LessonCard).where(LessonCard.lesson_type == "recorded").order_by(LessonCard.sort_order)
    ).scalars():
        g = lesson.part_group or lesson.code
        info = groups.setdefault(g, {"done": 0, "total": 0})
        info["total"] += 1
        if (lesson.id, "recorded_done") in acts:
            info["done"] += 1
    for g, info in groups.items():
        todos.append(
            {
                "kind": "recorded",
                "part_group": g,
                "title": _recorded_group_title(g),
                "done_count": info["done"],
                "total": info["total"],
                "acted": info["done"] >= info["total"],
            }
        )

    return {"progress": progress, "next_lesson": next_lesson_payload, "todos": todos}


def _recorded_group_title(group: str) -> str:
    names = {
        "D-1": "录播 D01–D06 · 模型 API 工程",
        "D-2": "录播 D07–D19 · 应用开发",
        "D-3": "录播 D20–D27 · 工程化与交付",
    }
    return names.get(group, f"录播 {group}")


def _iso(dt):
    from app.timeutil import to_iso

    return to_iso(dt)


def preview_read_rate(db: Session, student_id: int, now=None) -> float | None:
    """预习已读率（运营口径，02 文档 §4）：
    分母 = 已到 T-2 的已排课时数；分子 = 其中标记 preview_read 的数。
    """
    now = now or now_utc()
    rows = db.execute(
        select(Schedule.lesson_card_id, Schedule.scheduled_at).where(
            Schedule.student_id == student_id, Schedule.status == "scheduled"
        )
    ).all()
    denominator = 0
    for card_id, scheduled_at in rows:
        if scheduled_at is not None and preview_unlocked(scheduled_at, now):
            denominator += 1
    if denominator == 0:
        return None
    numerator = 0
    for card_id, scheduled_at in rows:
        if scheduled_at is not None and preview_unlocked(scheduled_at, now) and has_activity(
            db, student_id, card_id, "preview_read"
        ):
            numerator += 1
    return numerator / denominator


def mask_email(email: str) -> str:
    """邮箱脱敏（03 文档 admin 接口示例：y***@example.com）。"""
    local, _, domain = email.partition("@")
    if not domain:
        return email[:1] + "***"
    return f"{local[:1]}***@{domain}"
