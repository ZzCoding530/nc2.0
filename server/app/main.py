"""FastAPI 入口：挂路由 + 启动初始化（建表/种子/定时任务）+ 本地演示静态托管。"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import admin, auth, student
from app.config import get_settings
from app.database import SessionLocal
from app.errors import register_error_handler

WORKSPACE = Path(__file__).resolve().parents[2]
H5_DIST = WORKSPACE / "student-h5" / "dist" / "build" / "h5"
ADMIN_DIST = WORKSPACE / "admin-web" / "dist"


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


# ---------------- 本地演示静态托管（生产由 Caddy 反代，此处仅为单端口联调） ----------------

def _serve_file_or_index(base: Path, sub: str) -> FileResponse:
    file = base / sub
    if file.is_file():
        return FileResponse(file)
    index = base / "index.html"
    if index.is_file():
        return FileResponse(index)
    from fastapi import HTTPException

    raise HTTPException(status_code=404)


@app.get("/admin/{full_path:path}")
def admin_static(full_path: str):
    return _serve_file_or_index(ADMIN_DIST, full_path)


@app.get("/{full_path:path}")
def h5_static(full_path: str):
    return _serve_file_or_index(H5_DIST, full_path)
