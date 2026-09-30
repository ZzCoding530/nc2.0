"""认证与依赖：学员 / 运营双 JWT secret，互不通用（03 文档 §1、§5）。"""
from datetime import timedelta

import bcrypt
import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.errors import AppError
from app.models import StaffUser, Student
from app.timeutil import now_utc


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_jwt(subject: int, scope: str, days: int | None = None) -> str:
    settings = get_settings()
    secret = settings.jwt_secret_student if scope == "student" else settings.jwt_secret_staff
    expire_days = days if days is not None else settings.jwt_expire_days
    payload = {
        "sub": str(subject),
        "scope": scope,
        "exp": now_utc() + timedelta(days=expire_days),
        "iat": now_utc(),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _decode_jwt(request: Request, scope: str) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AppError("UNAUTHORIZED")
    token = auth.removeprefix("Bearer ").strip()
    settings = get_settings()
    secret = settings.jwt_secret_student if scope == "student" else settings.jwt_secret_staff
    other_secret = settings.jwt_secret_staff if scope == "student" else settings.jwt_secret_student
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AppError("UNAUTHORIZED", "登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        # 双 token 体系不互通：能被另一 scope secret 验签 → 越权（03 文档 FORBIDDEN）
        try:
            other = jwt.decode(token, other_secret, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            other = None
        if other is not None and other.get("scope") != scope:
            raise AppError("FORBIDDEN")
        raise AppError("UNAUTHORIZED")
    if payload.get("scope") != scope:
        raise AppError("FORBIDDEN")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        raise AppError("UNAUTHORIZED")


def get_current_student(request: Request, db: Session = Depends(get_db)) -> Student:
    student_id = _decode_jwt(request, "student")
    student = db.get(Student, student_id)
    if student is None:
        raise AppError("UNAUTHORIZED")
    return student


def get_current_staff(request: Request, db: Session = Depends(get_db)) -> StaffUser:
    staff_id = _decode_jwt(request, "staff")
    staff = db.get(StaffUser, staff_id)
    if staff is None:
        raise AppError("UNAUTHORIZED")
    return staff
