"""学员认证全链路（03 文档 §2）：注册→验证邮件→激活→登录→重置。"""
import re
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services import email_service as mail
from app.deps import create_jwt, get_db, hash_password, verify_password
from app.errors import AppError
from app.models import EmailToken, Student, Whitelist
from app.schemas import LoginIn, RegisterIn, ResetPasswordIn, ResendIn
from app.timeutil import now_utc

router = APIRouter(prefix="/auth", tags=["auth"])

PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")

# 登录失败锁定（03 文档 §1.1 / §5）：连续 5 次锁 10 分钟
MAX_FAILS = 5
LOCK_MINUTES = 10
_login_failures: dict[str, dict] = {}


def reset_login_lock_state() -> None:
    """测试辅助：清空内存锁定状态。"""
    _login_failures.clear()


def _is_locked(email: str, now) -> bool:
    state = _login_failures.get(email.lower())
    if not state:
        return False
    if state["count"] < MAX_FAILS:
        return False
    return now < state["lock_until"]


def _record_failure(email: str, now) -> None:
    key = email.lower()
    state = _login_failures.setdefault(key, {"count": 0, "lock_until": now})
    state["count"] += 1
    if state["count"] >= MAX_FAILS:
        state["lock_until"] = now + timedelta(minutes=LOCK_MINUTES)


def _validate_password_strength(password: str) -> None:
    if not PASSWORD_RE.match(password):
        raise AppError("VALIDATION_ERROR", "密码需至少 8 位且同时包含字母和数字")


def _student_payload(student: Student) -> dict:
    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
        "cohort": student.cohort.name,
    }


@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    _validate_password_strength(payload.password)
    email = payload.email.lower()

    if db.execute(select(Student.id).where(Student.email == email)).first() is not None:
        raise AppError("EMAIL_TAKEN")
    entry = db.execute(select(Whitelist).where(Whitelist.email == email)).scalar_one_or_none()
    if entry is None or entry.used_by is not None:
        raise AppError("EMAIL_NOT_WHITELISTED")

    student = Student(
        email=email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        cohort_id=entry.cohort_id,
        status="pending",
    )
    db.add(student)
    db.flush()

    token = mail.make_email_token(db, student, "verify", now_utc() + timedelta(hours=24))
    db.flush()
    mail.send_email(
        db, student, "verify", None,
        subject="完成注册验证 · NiceOffer 学员中心",
        body=(
            f"你好 {student.name}，点击以下链接完成注册（24 小时内有效）：\n"
            f"{mail.verify_link(token)}\n"
            f"如果不是你本人操作，请忽略本邮件。"
        ),
        retry_delay=0,
    )

    entry.used_by = student.id
    db.commit()
    return {"message": "验证邮件已发送，请 24 小时内激活"}


@router.post("/verify/{token}")
def verify(token: str, db: Session = Depends(get_db)):
    now = now_utc()
    record = _consume_token(db, token, "verify", now)
    student = db.get(Student, record.student_id)
    if student.status == "pending":
        student.status = "active"
    student.last_login_at = now
    db.commit()
    return {"token": create_jwt(student.id, "student"), "student": _student_payload(student)}


@router.post("/resend-verification")
def resend_verification(payload: ResendIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    now = now_utc()
    student = db.execute(select(Student).where(Student.email == email)).scalar_one_or_none()
    # 不泄露存在性：未注册邮箱同样返回成功
    if student is not None and student.status == "pending":
        last = _last_verify_sent_at(db, student.id)
        if last is not None and now - last < timedelta(seconds=60):
            return {"message": "发送过于频繁，请稍后再试"}
        token = mail.make_email_token(db, student, "verify", now + timedelta(hours=24))
        db.flush()
        mail.send_email(
            db, student, "verify", None,
            subject="完成注册验证 · NiceOffer 学员中心",
            body=(
                f"你好 {student.name}，点击以下链接完成注册（24 小时内有效）：\n"
                f"{mail.verify_link(token)}\n"
                f"如果不是你本人操作，请忽略本邮件。"
            ),
            retry_delay=0,
        )
    return {"message": "如该邮箱已注册，验证邮件已重新发送，请查收"}


def _last_verify_sent_at(db: Session, student_id: int):
    from app.models import EmailLog

    return db.execute(
        select(EmailLog.created_at)
        .where(EmailLog.student_id == student_id, EmailLog.mail_type == "verify")
        .order_by(EmailLog.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    now = now_utc()

    if _is_locked(email, now):
        raise AppError("ACCOUNT_LOCKED")

    student = db.execute(select(Student).where(Student.email == email)).scalar_one_or_none()
    if student is None or not verify_password(payload.password, student.password_hash):
        _record_failure(email, now)
        raise AppError("INVALID_CREDENTIALS")

    if student.status == "pending":
        raise AppError("ACCOUNT_PENDING")
    if student.status in ("suspended", "graduated"):
        raise AppError("FORBIDDEN", "账号状态异常，请联系班主任")

    _login_failures.pop(email, None)
    student.last_login_at = now
    db.commit()
    return {
        "token": create_jwt(student.id, "student"),
        "student": {
            **_student_payload(student),
            "cohort_start_date": student.cohort.start_date,
        },
    }


@router.post("/forgot-password")
def forgot_password(payload: ResendIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    now = now_utc()
    student = db.execute(select(Student).where(Student.email == email)).scalar_one_or_none()
    if student is not None:
        token = mail.make_email_token(db, student, "reset", now + timedelta(hours=24))
        db.flush()
        mail.send_email(
            db, student, "reset", None,
            subject="重置你的密码 · NiceOffer 学员中心",
            body=f"点击以下链接设置新密码（24 小时内有效）：{mail.reset_link(token)}",
            retry_delay=0,
        )
    return {"message": "如该邮箱已注册，重置邮件已发送，请查收"}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    _validate_password_strength(payload.new_password)
    now = now_utc()
    record = _consume_token(db, payload.token, "reset", now)
    student = db.get(Student, record.student_id)
    student.password_hash = hash_password(payload.new_password)
    db.commit()
    reset_login_lock_state()
    return {"message": "密码已更新，请重新登录"}


def _consume_token(db: Session, token: str, purpose: str, now) -> EmailToken:
    record = db.execute(
        select(EmailToken).where(EmailToken.token == token, EmailToken.purpose == purpose)
    ).scalar_one_or_none()
    if record is None or record.used_at is not None:
        raise AppError("TOKEN_INVALID")
    if now >= record.expires_at:
        raise AppError("TOKEN_EXPIRED")
    record.used_at = now
    return record



