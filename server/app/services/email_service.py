"""邮件发送服务（04 文档 §5–6，05 文档 §2.2 降级规范）。

- 业务代码只允许经 EmailSender 抽象发邮件，禁止直接 import smtplib；
- 降级只换「怎么送达」，email_log 落库、24h 防重、失败重试、token 逻辑全部照常执行；
- 切换后端只改 .env 的 EMAIL_BACKEND，不改业务代码。
"""
import smtplib
import time
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Protocol
from urllib.parse import quote

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmailLog, EmailToken, LessonCard, SiteConfig, Student
from app.timeutil import (
    fmt_time_cn,
    now_utc,
    to_naive_utc,
    weekday_cn,
)


class SendResult:
    def __init__(self, ok: bool, error: str | None = None):
        self.ok = ok
        self.error = error


class EmailMeta:
    def __init__(self, student_id: int | None, mail_type: str, lesson_card_id: int | None):
        self.student_id = student_id
        self.mail_type = mail_type
        self.lesson_card_id = lesson_card_id


class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str, meta: EmailMeta) -> SendResult: ...


class ConsoleSender:
    """最简兜底：打印终端，仍算 sent（05 文档 §2.2）。"""

    def send(self, to: str, subject: str, body: str, meta: EmailMeta) -> SendResult:
        print(f"===== EMAIL [{meta.mail_type}] to {to} =====\nSubject: {subject}\n{body}\n=====")
        return SendResult(ok=True)


class SMTPEmailSender:
    """生产：真实 SMTP（腾讯企业邮箱）。"""

    def __init__(self, host: str, port: int, user: str, password: str, from_name: str, use_ssl: bool):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_name = from_name
        self.use_ssl = use_ssl

    def send(self, to: str, subject: str, body: str, meta: EmailMeta) -> SendResult:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr((str(Header(self.from_name, "utf-8")), self.user))
        msg["To"] = to
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=15)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=15)
            try:
                if self.password:
                    server.starttls() if not self.use_ssl else None
                    server.login(self.user, self.password)
                server.sendmail(self.user, [to], msg.as_string())
            finally:
                server.quit()
        except Exception as exc:  # noqa: BLE001 - SMTP 异常统一进 error_msg
            return SendResult(ok=False, error=str(exc))
        return SendResult(ok=True)


class MailpitSender(SMTPEmailSender):
    """本地推荐：发到 localhost:1025，浏览器 localhost:8025 看收件箱。"""

    def __init__(self, host: str = "localhost", port: int = 1025):
        super().__init__(host, port, "", "", get_settings().mail_from_name, use_ssl=False)


def get_sender() -> EmailSender:
    settings = get_settings()
    backend = settings.email_backend.lower()
    if backend == "smtp":
        return SMTPEmailSender(
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_user,
            settings.smtp_pass,
            settings.mail_from_name,
            settings.smtp_ssl or settings.smtp_port == 465,
        )
    if backend == "mailpit":
        return MailpitSender(settings.smtp_host, settings.smtp_port)
    return ConsoleSender()


def get_config(db: Session, key: str, default: str = "") -> str:
    row = db.get(SiteConfig, key)
    return row.value if row else default


# ---------------------------------------------------------------- links

def h5_url(path: str) -> str:
    return f"{get_settings().app_base_url}/#/{path}"


def make_email_token(db: Session, student: Student, purpose: str, expires_at) -> str:
    import secrets

    token = EmailToken(
        student_id=student.id,
        token=secrets.token_urlsafe(32),
        purpose=purpose,
        expires_at=to_naive_utc(expires_at),
    )
    db.add(token)
    db.flush()
    return token.token


def magic_link(db: Session, student: Student, to_path: str) -> str:
    """邮件直达链接：7 天有效（04 文档 §5）。"""
    from datetime import timedelta

    token_str = make_email_token(db, student, "magic_link", now_utc() + timedelta(days=7))
    return h5_url(f"pages/l/index?token={token_str}&to={quote(to_path, safe='')}")


def verify_link(token: str) -> str:
    return h5_url(f"pages/verify/index?token={token}")


def reset_link(token: str) -> str:
    return h5_url(f"pages/reset/index?token={token}")


def ics_link(schedule_id: int) -> str:
    return f"{get_settings().app_base_url}/api/schedules/{schedule_id}/calendar.ics"


# ---------------------------------------------------------------- templates

def render_email(db: Session, mail_type: str, ctx: dict) -> tuple[str, str]:
    """六类模板（04 文档 §6）。返回 (subject, body)。"""
    qa = get_config(db, "qa_contact", "qa@example.com")

    if mail_type == "verify":
        subject = "完成注册验证 · NiceOffer 学员中心"
        body = (
            f"你好 {ctx['name']}，点击以下链接完成注册（24 小时内有效）：\n"
            f"{ctx['verify_link']}\n"
            f"如果不是你本人操作，请忽略本邮件。"
        )
    elif mail_type == "reset":
        subject = "重置你的密码 · NiceOffer 学员中心"
        body = f"点击以下链接设置新密码（24 小时内有效）：{ctx['reset_link']}"
    elif mail_type == "welcome":
        subject = f"欢迎加入 NiceOffer {ctx['cohort_name']}"
        body = (
            f"三步开始学习：\n"
            f"① 登录学员中心：{ctx['login_url']}\n"
            f"② 查看你的课程地图：{ctx['map_link']}\n"
            f"③ 完成第一节预习：{ctx['first_preview_link']}\n"
            f"班主任联系方式：{ctx['qa_contact']}"
        )
    elif mail_type == "schedule_confirm":
        subject = f"已排课：{ctx['lesson_code']} {ctx['lesson_title']} · {ctx['time_cn']}"
        body = (
            f"你的 {ctx['lesson_code']}《{ctx['lesson_title']}》定于 {ctx['time_cn']}"
            f"（{ctx['weekday_cn']}），\n"
            f"上课链接：{ctx['meeting_link']}。加入日历：{ctx['ics_link']}"
        )
    elif mail_type == "schedule_change":
        subject = f"上课时间有调整：{ctx['lesson_code']} {ctx['lesson_title']}"
        body = (
            f"原时间 {ctx['old_time_cn']} → 新时间 {ctx['new_time_cn']}，链接不变。\n"
            f"上课链接：{ctx['meeting_link']}"
        )
    elif mail_type == "preview_reminder":
        subject = f"[{ctx['lesson_code']}] 预习已解锁，上课前完成三问预写"
        body = (
            f"{ctx['lesson_code']}《{ctx['lesson_title']}》将于 {ctx['time_cn']} 上课，\n"
            f"预习已解锁（三问预写 + 关键词）：{ctx['preview_link']}"
        )
    elif mail_type == "class_reminder":
        subject = f"今晚 {ctx['time_cn']} 上课 · {ctx['lesson_code']} {ctx['lesson_title']}"
        body = (
            f"今天 {ctx['time_cn']} 有你的 1v1 课《{ctx['lesson_title']}》，"
            f"进入教室：{ctx['meeting_link']}"
        )
    else:
        raise ValueError(f"unknown mail_type: {mail_type}")

    body += f"\n\n本邮件为课程服务通知 · 如需退订联系 {qa}"
    return subject, body


def build_schedule_ctx(db: Session, schedule) -> dict:
    lesson = schedule.lesson_card
    return {
        "lesson_code": lesson.code,
        "lesson_title": lesson.title,
        "time_cn": fmt_time_cn(schedule.scheduled_at),
        "weekday_cn": weekday_cn(schedule.scheduled_at),
        "meeting_link": schedule.meeting_link,
        "ics_link": ics_link(schedule.id),
        "preview_link": magic_link(db, schedule.student, f"/pages/lesson/index?code={lesson.code}"),
    }


# ---------------------------------------------------------------- 发送（防重 + 重试 + 落库）

def _dup_log_exists(db: Session, student_id: int, mail_type: str, lesson_card_id: int | None, now) -> bool:
    from datetime import timedelta

    cond = and_(
        EmailLog.student_id == student_id,
        EmailLog.mail_type == mail_type,
        EmailLog.created_at > now - timedelta(hours=24),
    )
    cond = and_(cond, EmailLog.lesson_card_id.is_(None)) if lesson_card_id is None \
        else and_(cond, EmailLog.lesson_card_id == lesson_card_id)
    return db.execute(select(EmailLog.id).where(cond).limit(1)).first() is not None


def send_email(
    db: Session,
    student: Student,
    mail_type: str,
    lesson_card: LessonCard | None = None,
    *,
    subject: str | None = None,
    body: str | None = None,
    sender: EmailSender | None = None,
    now=None,
    retry_delay: float = 60.0,
) -> str:
    """统一发送入口：防重 → 落库 → 发送（失败重试 2 次）→ 状态流转。

    返回 'sent' | 'skipped' | 'failed'。subject/body 可 externally 传入（重发场景）。
    """
    now = now or now_utc()
    sender = sender or get_sender()

    if _dup_log_exists(db, student.id, mail_type, lesson_card.id if lesson_card else None, now):
        return "skipped"

    if subject is None or body is None:
        ctx = _build_ctx(db, student, mail_type, lesson_card)
        subject, body = render_email(db, mail_type, ctx)

    log = EmailLog(
        student_id=student.id,
        to_email=student.email,
        mail_type=mail_type,
        lesson_card_id=lesson_card.id if lesson_card else None,
        subject=subject,
        body=body,
        status="pending",
    )
    db.add(log)
    db.flush()

    result = sender.send(student.email, subject, body, EmailMeta(student.id, mail_type, log.lesson_card_id))
    retries = 0
    while not result.ok and retries < 2:
        retries += 1
        if retry_delay:
            time.sleep(retry_delay)
        result = sender.send(student.email, subject, body, EmailMeta(student.id, mail_type, log.lesson_card_id))

    log.retry_count = retries
    if result.ok:
        log.status = "sent"
        log.sent_at = now
    else:
        log.status = "failed"
        log.error_msg = (result.error or "")[:500]
    db.commit()
    return "sent" if result.ok else "failed"


def _build_ctx(db: Session, student: Student, mail_type: str, lesson_card: LessonCard | None) -> dict:
    from app.models import Schedule
    from sqlalchemy import select as _select

    ctx: dict = {"name": student.name}
    if mail_type in ("schedule_confirm", "schedule_change", "preview_reminder", "class_reminder"):
        schedule = db.execute(
            _select(Schedule).where(
                Schedule.student_id == student.id,
                Schedule.lesson_card_id == lesson_card.id,
            )
        ).scalar_one()
        ctx.update(build_schedule_ctx(db, schedule))
        if mail_type == "schedule_change":
            ctx["new_time_cn"] = fmt_time_cn(schedule.scheduled_at)
    if mail_type == "welcome":
        ctx.update(
            {
                "cohort_name": student.cohort.name,
                "login_url": get_settings().app_base_url,
                "map_link": magic_link(db, student, "/pages/map/index"),
                "first_preview_link": magic_link(db, student, "/pages/map/index"),
                "qa_contact": get_config(db, "qa_contact", "qa@example.com"),
            }
        )
    return ctx


def retry_email_log(db: Session, log: EmailLog, *, sender: EmailSender | None = None, now=None, retry_delay: float = 60.0) -> str:
    """失败重发（后台按钮 / 每小时定时）。直接用落库的 subject/body。"""
    now = now or now_utc()
    sender = sender or get_sender()
    student = db.get(Student, log.student_id) if log.student_id else None
    if student is None:
        log.status = "failed"
        log.error_msg = "student missing"
        db.commit()
        return "failed"
    result = sender.send(log.to_email, log.subject, log.body, EmailMeta(log.student_id, log.mail_type, log.lesson_card_id))
    if result.ok:
        log.status = "sent"
        log.sent_at = now
        log.error_msg = None
    else:
        log.retry_count += 1
        log.error_msg = (result.error or "")[:500]
    db.commit()
    return "sent" if result.ok else "failed"


def send_schedule_change(
    db: Session, student: Student, lesson_card: LessonCard, old_at, new_at, schedule
) -> str:
    schedule_for_ctx = schedule
    subject, body = render_email(
        db,
        "schedule_change",
        {
            "lesson_code": lesson_card.code,
            "lesson_title": lesson_card.title,
            "old_time_cn": fmt_time_cn(old_at),
            "new_time_cn": fmt_time_cn(new_at),
            "meeting_link": schedule_for_ctx.meeting_link,
            "ics_link": ics_link(schedule_for_ctx.id),
            "preview_link": "",
        },
    )
    return send_email(
        db, student, "schedule_change", lesson_card, subject=subject, body=body
    )
