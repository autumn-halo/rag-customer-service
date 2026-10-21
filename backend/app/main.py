"""FastAPI 应用入口：组装路由、中间件与启动任务。"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import auth, chat, conversations, documents, users
from app.config import settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import User
from app.rag import bm25
from app.services import queue


def _seed_admin(db: Session) -> None:
    """首次启动时自动创建管理员账号（用户名/密码来自 .env）。"""
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    if admin is None:
        db.add(
            User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                role="admin",
            )
        )
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建目录、建表、播种管理员、恢复 BM25 索引、重启后台入库 worker
    settings.ensure_runtime_dirs()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _seed_admin(db)
        stale_ids = queue.recover_stale(db)
        bm25.rebuild_from_db(db)
    queue.start_worker()
    for doc_id in stale_ids:
        queue.enqueue(doc_id)
    yield
    # 关闭：停止后台入库 worker
    await queue.stop_worker()


app = FastAPI(
    title="RAG 电商知识库问答系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")


@app.get("/api/health")
def health():
    """健康检查：Docker healthcheck 与前端探活复用。"""
    return {
        "status": "ok",
        "dashscope_configured": bool(settings.dashscope_api_key),
    }


# ===== 生产模式：托管前端构建产物（Docker 单容器部署用）=====
# 开发模式（vite dev server）下 static 目录不存在，自动跳过。
_STATIC_DIR = Path(__file__).parent / "static"

if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """单页应用兜底：非 API 路径一律回退到 index.html（支持前端路由刷新）。"""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="接口不存在")
        file = _STATIC_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_STATIC_DIR / "index.html")
else:

    @app.get("/")
    def dev_root():
        """开发模式：前端由 vite dev server 提供，此处只给友好提示。"""
        return {
            "name": "RAG 电商知识库问答系统（开发模式）",
            "tip": "前端页面请访问 http://localhost:5173（先运行 start.bat）",
            "docs": "/docs",
            "health": "/api/health",
        }
