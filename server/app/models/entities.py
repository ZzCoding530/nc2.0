"""SQLAlchemy 模型，严格对照 02 文档 §2 DDL。

偏离记录（见 DEVLOG 决策区）：
- email_log 额外增加 body 列：失败重发 / 运营核对需要原文，DDL 未含，属加列不改列，兼容文档结构。
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.timeutil import now_utc


class Module(Base):
    __tablename__ = "module"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    subtitle: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class LessonCard(Base):
    __tablename__ = "lesson_card"
    __table_args__ = (
        Index("idx_lesson_module", "module_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("module.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    lesson_type: Mapped[str] = mapped_column(Text, nullable=False)
    duration_min: Mapped[int | None] = mapped_column(Integer)
    effort_note: Mapped[str] = mapped_column(Text, default="")
    content_summary: Mapped[str] = mapped_column(Text, nullable=False)
    project_stage: Mapped[str] = mapped_column(Text, default="")
    preview: Mapped[str | None] = mapped_column(Text)  # JSON 字符串
    homework_def: Mapped[str] = mapped_column(Text, default="")
    deps: Mapped[str] = mapped_column(Text, default="")
    part_group: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    module: Mapped[Module] = relationship()
    materials: Mapped[list["Material"]] = relationship(
        order_by="Material.sort_order", cascade="all, delete-orphan"
    )


class Material(Base):
    __tablename__ = "material"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_card_id: Mapped[int] = mapped_column(ForeignKey("lesson_card.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    mat_type: Mapped[str] = mapped_column(Text, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Cohort(Base):
    __tablename__ = "cohort"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    start_date: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")


class Student(Base):
    __tablename__ = "student"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','active','suspended','graduated')",
            name="ck_student_status",
        ),
        Index("idx_student_cohort", "cohort_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohort.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_utc)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    cohort: Mapped[Cohort] = relationship()


class Whitelist(Base):
    __tablename__ = "whitelist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohort.id"), nullable=False)
    used_by: Mapped[int | None] = mapped_column(ForeignKey("student.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_utc)


class Schedule(Base):
    __tablename__ = "schedule"
    __table_args__ = (
        UniqueConstraint("student_id", "lesson_card_id", name="uq_schedule_student_lesson"),
        Index("idx_schedule_next", "student_id", "status", "scheduled_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), nullable=False)
    lesson_card_id: Mapped[int] = mapped_column(ForeignKey("lesson_card.id"), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    meeting_link: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="planned")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("staff_user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_utc)

    student: Mapped[Student] = relationship()
    lesson_card: Mapped[LessonCard] = relationship()


class Activity(Base):
    __tablename__ = "activity"
    __table_args__ = (
        UniqueConstraint("student_id", "lesson_card_id", "act_type", name="uq_activity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), nullable=False)
    lesson_card_id: Mapped[int] = mapped_column(ForeignKey("lesson_card.id"), nullable=False)
    act_type: Mapped[str] = mapped_column(Text, nullable=False)
    acted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_utc)


class EmailToken(Base):
    __tablename__ = "email_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), nullable=False)
    token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)


class EmailLog(Base):
    __tablename__ = "email_log"
    __table_args__ = (
        CheckConstraint(
            "mail_type IN ('verify','reset','welcome','schedule_confirm',"
            "'schedule_change','preview_reminder','class_reminder')",
            name="ck_email_log_mail_type",
        ),
        Index("idx_email_dedup", "student_id", "mail_type", "lesson_card_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("student.id"))
    to_email: Mapped[str] = mapped_column(Text, nullable=False)
    mail_type: Mapped[str] = mapped_column(Text, nullable=False)
    lesson_card_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_card.id"))
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_msg: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_utc)
    # 偏离 02 DDL 的新增列：保存正文供失败重发（DEVLOG 决策记录）
    body: Mapped[str] = mapped_column(Text, default="")


class StaffUser(Base):
    __tablename__ = "staff_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="staff")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_utc)


class SiteConfig(Base):
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_utc)
