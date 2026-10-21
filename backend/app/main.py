"""FastAPI 应用入口：组装路由、中间件与启动任务。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import auth, chat, conversations, users
from app.config import settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import User


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
    # 启动：建目录、建表、播种管理员、启动后台入库 worker（入库 worker 在阶段 4 加入）
    settings.ensure_runtime_dirs()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _seed_admin(db)
    yield
    # 关闭：清理任务（阶段 4 加入）


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


@app.get("/")
def root():
    return {"name": "RAG 电商知识库问答系统", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health")
def health():
    """健康检查：Docker healthcheck 与前端探活复用。"""
    return {
        "status": "ok",
        "dashscope_configured": bool(settings.dashscope_api_key),
    }
