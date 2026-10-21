"""数据库引擎与会话管理。

换 MySQL 只需修改 .env 里的 DATABASE_URL，业务代码零改动。
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

is_sqlite = settings.db_path.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.db_path,
    connect_args=connect_args,
    pool_pre_ping=True,  # 取连接前先探测有效性，防止断连报错
)

if is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        if settings.sqlite_wal:
            # WAL 提升读写并发；journal_mode 会持久化到数据库文件头
            cursor.execute("PRAGMA journal_mode=WAL")
        else:
            # 数据库文件可能已被开发模式烙成 WAL，容器内必须显式切回 DELETE：
            # bind mount 不支持 WAL 所需的共享内存，否则随机 disk I/O error
            cursor.execute("PRAGMA journal_mode=DELETE")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db():
    """FastAPI 依赖：每个请求一个数据库会话，请求结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
