"""请求体 Pydantic 模型（字段名与 03 文档严格一致，不一致视为 bug）。"""
from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=50)
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ResendIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str


class ActivityIn(BaseModel):
    act_type: str


class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str


class AdminChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


class ImportWhitelistIn(BaseModel):
    emails: list[EmailStr]
    cohort_id: int


class ScheduleUpsertIn(BaseModel):
    student_id: int
    lesson_card_id: int | None = None
    lesson_code: str | None = None
    scheduled_at: str | None = None
    meeting_link: str | None = None
    status: str | None = None


class ScheduleUpdateIn(BaseModel):
    scheduled_at: str | None = None
    meeting_link: str | None = None
    status: str | None = None


class SendReminderIn(BaseModel):
    mail_type: str
