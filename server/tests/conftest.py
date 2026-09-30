"""测试环境（05 文档 §3.4）：独立临时库 + 种子，不碰开发库 data/app.db。"""
import os

os.environ["TESTING"] = "true"
os.environ["EMAIL_BACKEND"] = "console"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.database import Base
from app.deps import get_db
from app.api.auth import reset_login_lock_state
from app.main import app
from app.seeds.seed import seed


@pytest.fixture(autouse=True)
def _reset_lock_state():
    reset_login_lock_state()
    yield
    reset_login_lock_state()


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestSession()
    seed(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------- 通用 helpers ----------------

WHITELIST_EMAIL = "student@example.com"
STAFF_EMAIL = "admin@example.com"
STAFF_PASSWORD = "ChangeMe123!"


def add_whitelist(db, email=WHITELIST_EMAIL, cohort_name="202610 期"):
    from app.models import Cohort, Whitelist

    cohort = db.query(Cohort).filter_by(name=cohort_name).one()
    db.add(Whitelist(email=email, cohort_id=cohort.id))
    db.commit()


def register_and_activate(client, db, email=WHITELIST_EMAIL, name="同学", password="Passw0rd!"):
    """注册 + 激活，返回 (token, student_id)。"""
    from app.models import EmailToken, Student

    r = client.post("/api/auth/register", json={"email": email, "name": name, "password": password})
    assert r.status_code == 200, r.text
    token_row = (
        db.query(EmailToken)
        .join(Student, EmailToken.student_id == Student.id)
        .filter(Student.email == email, EmailToken.purpose == "verify")
        .order_by(EmailToken.id.desc())
        .first()
    )
    r = client.post(f"/api/auth/verify/{token_row.token}")
    assert r.status_code == 200, r.text
    data = r.json()
    return data["token"], data["student"]["id"]


def staff_login(client):
    r = client.post("/api/admin/login", json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def schedule_lesson(client, db, student_id, code, scheduled_at, meeting_link="https://meeting.example.com/x"):
    r = client.post(
        "/api/admin/schedules",
        headers={"Authorization": f"Bearer {staff_login(client)}"},
        json={
            "student_id": student_id,
            "lesson_code": code,
            "scheduled_at": scheduled_at,
            "meeting_link": meeting_link,
            "status": "scheduled",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()
