"""集中管理全部配置：从 backend/.env 读取，未配置的字段使用默认值。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（本文件位于 backend/app/config.py）
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用配置。所有字段均可通过 .env 文件或环境变量覆盖。"""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 阿里云百炼 DashScope ----
    dashscope_api_key: str = ""
    model_chat: str = "qwen-plus"
    model_embedding: str = "text-embedding-v3"
    embedding_dimensions: int = 1024
    model_rerank: str = "qwen3-rerank"
    rerank_top_n: int = 5
    # qwen3-rerank 评分范围 0~1。≥阈值 → 检索结果可信，严格模式带引用作答；
    # <阈值 → 按意图分流（商品关键词 → 兜底话术；其他 → 自由对话）
    rerank_threshold: float = 0.35

    # ---- 安全 ----
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_hours: int = 24
    admin_username: str = "admin"
    admin_password: str = "123456"

    # ---- 存储 ----
    database_url: str = ""  # 空则使用默认 sqlite 路径
    chroma_dir: str = ""  # 空则使用默认路径
    upload_dir: str = ""  # 空则使用默认路径
    max_upload_mb: int = 20
    max_chunks_per_doc: int = 5000

    # ---- 检索参数 ----
    chunk_size: int = 500
    chunk_overlap: int = 80
    vector_top_k: int = 20
    bm25_top_k: int = 20
    rrf_k: int = 60
    final_top_k: int = 5
    context_max_chars: int = 6000
    history_turns: int = 3

    # ---- 缓存与限流 ----
    cache_ttl_seconds: int = 3600
    cache_max_entries: int = 128
    rate_limit_chat_per_min: int = 20
    rate_limit_login_per_min: int = 5

    # ---- 跨域 ----
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ============ 派生属性（统一路径解析，避免相对路径受启动目录影响）============
    @property
    def data_dir(self) -> Path:
        return BACKEND_DIR / "data"

    @property
    def db_path(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'app.db').as_posix()}"

    @property
    def chroma_path(self) -> str:
        return str(self.chroma_dir or self.data_dir / "chroma")

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir) if self.upload_dir else self.data_dir / "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_runtime_dirs(self) -> None:
        """创建运行时目录（SQLite/Chroma 都不会自动建父目录）。"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_path.mkdir(parents=True, exist_ok=True)
        Path(self.chroma_path).mkdir(parents=True, exist_ok=True)


settings = Settings()
