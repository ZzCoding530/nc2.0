"""FastAPI 入口：挂路由 + 启动初始化（建表/种子/定时任务）。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, student
from app.config import get_settings
from app.database import SessionLocal
from app.errors import register_error_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.testing:
        from app.seeds.seed import init_db

        init_db()

        from app.services.scheduler import register_scheduler

        register_scheduler(SessionLocal)
    yield


app = FastAPI(title="NiceOffer 交付系统 API", version="1.0", lifespan=lifespan)
register_error_handler(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(student.router, prefix="/api")
app.include_router(admin.public_router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}
