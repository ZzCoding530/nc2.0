"""幂等种子脚本（02 文档 §3）：按 code/name upsert，重跑不重复。
用法：python -m app.seeds.seed
"""
import json
import os

from sqlalchemy import select

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.deps import hash_password
from app.models import Cohort, LessonCard, Material, Module, SiteConfig, StaffUser


def seed(db) -> dict:
    path = os.path.join(os.path.dirname(__file__), "lessons_seed.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    counts = {"module": 0, "lesson_card": 0, "material": 0, "cohort": 0, "staff_user": 0, "config": 0}

    module_ids: dict[str, int] = {}
    for m in data["modules"]:
        row = db.execute(select(Module).where(Module.code == m["code"])).scalar_one_or_none()
        if row is None:
            row = Module(**m)
            db.add(row)
            db.flush()
            counts["module"] += 1
        else:
            row.title, row.subtitle, row.sort_order = m["title"], m["subtitle"], m["sort_order"]
        module_ids[m["code"]] = row.id

    card_ids: dict[str, int] = {}
    for lc in data["lesson_cards"]:
        payload = {k: v for k, v in lc.items() if k != "module_code"}
        payload["module_id"] = module_ids[lc["module_code"]]
        row = db.execute(select(LessonCard).where(LessonCard.code == lc["code"])).scalar_one_or_none()
        if row is None:
            row = LessonCard(**payload)
            db.add(row)
            db.flush()
            counts["lesson_card"] += 1
        else:
            for k, v in payload.items():
                setattr(row, k, v)
        card_ids[lc["code"]] = row.id

    existing_mats = {
        (m.lesson_card_id, m.title)
        for m in db.execute(select(Material)).scalars()
    }
    for mt in data["materials"]:
        key = (card_ids[mt["lesson_code"]], mt["title"])
        if key in existing_mats:
            continue
        db.add(Material(lesson_card_id=key[0], title=mt["title"], mat_type=mt["mat_type"],
                        required=mt["required"], url=mt["url"], sort_order=mt["sort_order"]))
        counts["material"] += 1

    cohort_data = data.get("cohort")
    if cohort_data and db.execute(select(Cohort).where(Cohort.name == cohort_data["name"])).scalar_one_or_none() is None:
        db.add(Cohort(**cohort_data))
        counts["cohort"] += 1

    settings = get_settings()
    if db.execute(select(StaffUser).where(StaffUser.email == settings.admin_bootstrap_email.lower())).scalar_one_or_none() is None:
        db.add(StaffUser(
            email=settings.admin_bootstrap_email.lower(),
            password_hash=hash_password(settings.admin_bootstrap_password),
            name="Rick",
            role="staff",
        ))
        counts["staff_user"] += 1

    for key, value in data.get("config", {}).items():
        row = db.get(SiteConfig, key)
        if row is None:
            db.add(SiteConfig(key=key, value=value))
            counts["config"] += 1

    db.commit()
    return counts


def init_db() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        counts = seed(db)
        print(f"[seed] {counts}")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
